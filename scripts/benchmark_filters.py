"""Benchmark the four candidate filters (feedback, constraints, csp, table) and check that they agree.

Each random game state (seeded) is a hidden answer and 1-4 random guesses; every method
computes the candidates consistent with that history from the full answer list.
Writes <out-dir>/filters.json and filters.md. Times are machine-dependent.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.agents import LetterFrequencyAgent  # noqa: E402
from wordle_tr.constraints import Constraints  # noqa: E402
from wordle_tr.feedback import feedback  # noqa: E402
from wordle_tr.filters import FILTER_NAMES, make_filter  # noqa: E402
from wordle_tr.pattern_table import PatternTable, compute_pattern_matrix  # noqa: E402
from wordle_tr.simulate import evaluate, random_histories  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402


def best_time(fn, repeat: int):
    """Fastest of ``repeat`` runs (seconds) and the result of the last run."""
    best = float("inf")
    for _ in range(repeat):
        t0 = perf_counter()
        result = fn()
        best = min(best, perf_counter() - t0)
    return best, result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=int, default=500, help="random game states (default 500)")
    parser.add_argument("--seed", type=int, default=1234, help="seed for the states (default 1234)")
    parser.add_argument("--repeat", type=int, default=3, help="time each call this many times, keep the fastest")
    parser.add_argument("--full-check", action="store_true",
                        help="compare every table cell with scalar feedback() (about 10 M calls)")
    parser.add_argument("--end-to-end", action="store_true",
                        help="time a full letter-frequency evaluation with each filter")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="output folder")
    args = parser.parse_args()

    answers, guesses = load_answers(), load_guesses()
    cells = len(guesses) * len(answers)
    report: dict = {"config": {"states": args.states, "seed": args.seed, "repeat": args.repeat,
                               "answers": len(answers), "guesses": len(guesses)}}

    # --- the pattern table: build from scratch, then load from the cache
    build_s, matrix = best_time(lambda: compute_pattern_matrix(guesses, answers), 1)
    PatternTable.load_or_build(guesses, answers)  # make sure the cache exists
    load_s, table = best_time(lambda: PatternTable.load_or_build(guesses, answers), args.repeat)
    assert (table.matrix == matrix).all()
    report["table"] = {"cells": cells, "megabytes": matrix.nbytes / 1e6, "build_s": build_s, "load_s": load_s}
    print(f"pattern table {len(guesses):,} x {len(answers):,} = {cells:,} cells ({matrix.nbytes / 1e6:.1f} MB): "
          f"built in {build_s:.2f} s, loaded from cache in {load_s * 1000:.1f} ms")

    # --- what one entropy turn (week 9) costs: every guess against every answer
    rng = random.Random(args.seed)
    pairs = [(rng.choice(guesses), rng.choice(answers)) for _ in range(200_000)]
    scalar_s, _ = best_time(lambda: [feedback(g, a) for g, a in pairs], args.repeat)
    per_call_us = scalar_s / len(pairs) * 1e6
    ids = table.all_ids()
    partition_s, _ = best_time(lambda: [table.partition_counts(g, ids) for g in range(len(guesses))], args.repeat)
    report["week9_turn"] = {"pairs": cells, "scalar_us_per_call": per_call_us,
                            "scalar_estimated_s": per_call_us * cells / 1e6,
                            "table_partition_counts_all_guesses_ms": partition_s * 1000}
    print(f"one week-9 turn: scalar feedback {per_call_us:.2f} us/call -> about "
          f"{per_call_us * cells / 1e6:.1f} s for all {cells:,} pairs; "
          f"table partition counts for all guesses {partition_s * 1000:.1f} ms")

    # --- the four filters on random states
    states = random_histories(answers, guesses, args.states, args.seed)
    filters = {name: make_filter(name, answers, guesses, table) for name in FILTER_NAMES}
    times: dict[str, list[float]] = {name: [] for name in FILTER_NAMES}
    times["table (ids only)"] = []
    mismatching = 0
    sizes, nodes_fc, nodes_bt = [], [], []
    for answer, history in states:
        results = {}
        for name, filter_fn in filters.items():
            t, results[name] = best_time(lambda: filter_fn(answers, history), args.repeat)
            times[name].append(t)

        def ids_only():
            ids = table.all_ids()
            for guess, pattern in history:
                ids = table.filter_ids(ids, guess, pattern)
            return ids

        t, _ = best_time(ids_only, args.repeat)
        times["table (ids only)"].append(t)
        expected = results["feedback"]
        mismatching += any(results[name] != expected for name in FILTER_NAMES) or answer not in expected
        sizes.append(len(expected))
        constraints = Constraints.from_history(history)
        nodes_fc.append(filters["csp"].solver.solve(constraints).nodes_expanded)
        nodes_bt.append(filters["csp"].solver.solve(constraints, forward_checking=False).nodes_expanded)

    reference_mean = statistics.fmean(times["feedback"])
    report["methods"] = {
        name: {"mean_ms": statistics.fmean(ts) * 1000, "median_ms": statistics.median(ts) * 1000,
               "speedup": reference_mean / statistics.fmean(ts)}
        for name, ts in times.items()
    }
    report["agreement"] = {"states": len(states), "mismatching_states": mismatching,
                           "mean_candidates": statistics.fmean(sizes)}
    report["csp"] = {"trie_nodes": filters["csp"].solver.trie.size,
                     "mean_nodes_forward_checking": statistics.fmean(nodes_fc),
                     "mean_nodes_backtracking_only": statistics.fmean(nodes_bt)}
    print(f"\n{len(states)} states (1-4 random guesses, seed {args.seed}), "
          f"mean {statistics.fmean(sizes):.1f} candidates left; mismatching states: {mismatching}")
    for name, m in report["methods"].items():
        print(f"  {name:<17} {m['mean_ms']:8.3f} ms   {m['speedup']:7.1f}x")
    print(f"  CSP nodes expanded: {statistics.fmean(nodes_fc):.1f} with forward checking, "
          f"{statistics.fmean(nodes_bt):.1f} without (trie: {filters['csp'].solver.trie.size:,} nodes)")

    # --- every cell of the table against scalar feedback
    report["full_check"] = None
    if args.full_check:
        t0 = perf_counter()
        mismatches = sum(sum(int(table.matrix[g, a] != feedback(guess, answer)) for a, answer in enumerate(answers))
                         for g, guess in enumerate(guesses))
        seconds = perf_counter() - t0
        t0 = perf_counter()
        scalar_only = [[feedback(guess, answer) for answer in answers] for guess in guesses]
        scalar_s = perf_counter() - t0
        del scalar_only
        report["full_check"] = {"cells": cells, "mismatches": mismatches, "check_s": seconds,
                                "scalar_all_pairs_s": scalar_s}
        print(f"\nfull check: {mismatches} mismatches in {cells:,} cells; "
              f"scalar feedback for all pairs took {scalar_s:.1f} s")

    # --- the whole letter-frequency evaluation with each filter
    report["end_to_end"] = None
    if args.end_to_end:
        report["end_to_end"] = {}
        reference_games = None
        print()
        for name in FILTER_NAMES:
            filter_fn = make_filter(name, answers, guesses, table)
            t0 = perf_counter()
            results = evaluate(LetterFrequencyAgent(), answers, guesses, filter_fn)
            wall = perf_counter() - t0
            games = [r.guesses for r in results]
            reference_games = reference_games or games
            entry = {"wall_s": wall, "filter_s": sum(t for r in results for t in r.filter_times),
                     "mean_guesses": statistics.fmean(r.num_guesses for r in results),
                     "identical_to_reference": games == reference_games}
            report["end_to_end"][name] = entry
            print(f"  frequency agent, {name:<11} filter: {wall:6.2f} s total, {entry['filter_s']:6.2f} s "
                  f"filtering, mean {entry['mean_guesses']:.4f}, identical: {entry['identical_to_reference']}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "filters.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    command = "python scripts/benchmark_filters.py" + "".join(f" {a}" for a in sys.argv[1:])
    write_markdown(args.out_dir / "filters.md", report, command)
    print(f"\nwrote {args.out_dir / 'filters.json'} and filters.md")


def write_markdown(path: Path, report: dict, command: str) -> None:
    cfg, tab, turn = report["config"], report["table"], report["week9_turn"]
    lines = [
        "# Filter benchmark", "",
        f"Generated by `{command}`. Times are machine-dependent (fastest of {cfg['repeat']} runs per call).", "",
        "## Pattern table", "",
        f"* {cfg['guesses']:,} guesses x {cfg['answers']:,} answers = {tab['cells']:,} cells, "
        f"{tab['megabytes']:.1f} MB (uint8)",
        f"* built (vectorised numpy): {tab['build_s']:.2f} s; loaded from the cache: {tab['load_s'] * 1000:.1f} ms",
        "", "## Cost of one entropy turn (every guess against every answer)", "",
        f"* scalar `feedback()`: {turn['scalar_us_per_call']:.2f} µs per call -> "
        f"{turn['scalar_estimated_s']:.1f} s for {turn['pairs']:,} pairs (estimated from 200,000 calls)",
    ]
    if report["full_check"]:
        lines.append(f"* scalar `feedback()` for all {turn['pairs']:,} pairs, measured: "
                     f"{report['full_check']['scalar_all_pairs_s']:.1f} s")
    lines += [
        f"* pattern table, `partition_counts` for all {cfg['guesses']:,} guesses: "
        f"{turn['table_partition_counts_all_guesses_ms']:.1f} ms",
        "", f"## Filtering {cfg['states']} random game states (seed {cfg['seed']})", "",
        f"Each state is a hidden answer and 1-4 random guesses; the candidates consistent with the "
        f"history are computed from all {cfg['answers']:,} answers "
        f"(on average {report['agreement']['mean_candidates']:.1f} remain).", "",
        "| Method | Mean ms / state | Median ms | Speed-up vs reference |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, m in report["methods"].items():
        lines.append(f"| {name} | {m['mean_ms']:.3f} | {m['median_ms']:.3f} | {m['speedup']:.1f}x |")
    csp = report["csp"]
    lines += [
        "", f"All four methods returned identical candidate sets: "
        f"{'yes' if report['agreement']['mismatching_states'] == 0 else 'NO'} "
        f"({report['agreement']['mismatching_states']} mismatching states).", "",
        f"CSP search: on average {csp['mean_nodes_forward_checking']:.1f} nodes expanded with forward checking, "
        f"{csp['mean_nodes_backtracking_only']:.1f} with backtracking only, out of {csp['trie_nodes']:,} trie nodes.",
    ]
    if report["full_check"]:
        fc = report["full_check"]
        lines += ["", "## Full check", "",
                  f"Every table cell compared with scalar `feedback()`: {fc['mismatches']} mismatches "
                  f"in {fc['cells']:,} cells."]
    if report["end_to_end"]:
        lines += ["", "## End to end: letter-frequency agent on all answers", "",
                  "| Filter | Total s | Filtering s | Mean guesses | Same games as reference |",
                  "| --- | ---: | ---: | ---: | --- |"]
        for name, e in report["end_to_end"].items():
            lines.append(f"| {name} | {e['wall_s']:.2f} | {e['filter_s']:.2f} | {e['mean_guesses']:.4f} | "
                         f"{'yes' if e['identical_to_reference'] else 'NO'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
