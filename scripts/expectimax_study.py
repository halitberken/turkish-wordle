"""Week 10 study: expectimax cost table (depth x width), and comparisons with the exact oracle.

1. Every (depth, width) configuration plays all answers: mean guesses, time, nodes.
2. Small candidate sets (seeded): oracle optimum vs entropy, most-parts and expectimax.
3. Fixed openers: the exact optimum V*(answers | opener) for a list of promising openers.
4. A lower bound on the optimum over all openers.

Writes <out-dir>/expectimax.json and expectimax.md. Times are machine-dependent.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.agents import ExpectimaxAgent, default_table, make_agent  # noqa: E402
from wordle_tr.alphabet import to_upper  # noqa: E402
from wordle_tr.feedback import feedback  # noqa: E402
from wordle_tr.filters import make_filter  # noqa: E402
from wordle_tr.oracle import Oracle, opener_lower_bound, policy_value  # noqa: E402
from wordle_tr.pattern_table import split  # noqa: E402
from wordle_tr.simulate import evaluate, random_histories, summarize  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--depths", type=int, nargs="+", default=[1, 2, 3], help="search depths (default 1 2 3)")
    parser.add_argument("--widths", type=int, nargs="+", default=[10, 25, 50],
                        help="beam widths, top-k guesses by entropy (default 10 25 50)")
    parser.add_argument("--small-sets", type=int, default=200, help="small candidate sets for the oracle check")
    parser.add_argument("--max-small", type=int, default=30, help="largest small set (default 30 candidates)")
    parser.add_argument("--openers", type=int, default=10,
                        help="solve exactly the top N openers by entropy and by number of parts (default 10)")
    parser.add_argument("--seed", type=int, default=1234, help="seed for the small sets (default 1234)")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="output folder")
    args = parser.parse_args()

    answers, guesses = load_answers(), load_guesses()
    table = default_table()
    all_ids = table.all_ids()
    filter_fn = make_filter("table", answers, guesses, table)
    report: dict = {"config": vars(args) | {"out_dir": str(args.out_dir)}}

    # --- reference agents (exact means, by following their choices through every pattern)
    reference = {}
    for name in ("entropy", "most_parts"):
        agent = make_agent(name, table=table)
        results = evaluate(agent, answers, guesses, filter_fn)
        reference[name] = {"agent": agent, "results": results, "summary": summarize(results, name)}
        print(f"{name:<11} mean {reference[name]['summary'].mean:.4f} opener {to_upper(results[0].guesses[0])}")
    report["reference"] = {name: {"mean": r["summary"].mean, "max": r["summary"].max,
                                  "opener": r["results"][0].guesses[0]} for name, r in reference.items()}
    entropy_games = {r.answer: r.num_guesses for r in reference["entropy"]["results"]}

    # --- 1. cost table
    report["grid"] = []
    print("\n depth width   mean    max  opener  first move s  total s   nodes  vs entropy (better/worse)")
    for depth in args.depths:
        for width in args.widths:
            agent = ExpectimaxAgent(table, depth=depth, width=width)
            t0 = perf_counter()
            agent.choose_guess([], answers)
            first_s = perf_counter() - t0
            predicted = agent.last_choice["expected_guesses"]
            results = evaluate(agent, answers, guesses, filter_fn)
            total_s = perf_counter() - t0
            s = summarize(results, "expectimax")
            better = sum(r.num_guesses < entropy_games[r.answer] for r in results)
            worse = sum(r.num_guesses > entropy_games[r.answer] for r in results)
            row = {"depth": depth, "width": width, "mean": s.mean, "max": s.max, "failures": s.failures,
                   "histogram": {str(k): v for k, v in s.histogram.items()}, "opener": results[0].guesses[0],
                   "predicted_at_opening": predicted, "first_move_s": first_s, "total_s": total_s,
                   "nodes": agent.nodes, "words_better_than_entropy": better, "words_worse_than_entropy": worse}
            report["grid"].append(row)
            print(f" {depth:5d} {width:5d}  {s.mean:.4f}  {s.max:3d}  {to_upper(row['opener']):<6} {first_s:11.1f}  "
                  f"{total_s:7.1f}  {agent.nodes:6d}  {better}/{worse}", flush=True)

    # --- 2. small candidate sets against the oracle
    oracle = Oracle(table)
    sets: dict[bytes, np.ndarray] = {}
    for _, history in random_histories(answers, guesses, 20 * args.small_sets, args.seed):
        ids = all_ids
        for guess, pattern in history:
            ids = table.filter_ids(ids, guess, pattern)
        if 3 <= len(ids) <= args.max_small:
            sets.setdefault(ids.tobytes(), ids)
        if len(sets) == args.small_sets:
            break
    small = list(sets.values())
    policies = {"entropy": make_agent("entropy", table=table), "most_parts": make_agent("most_parts", table=table)}
    policies |= {f"expectimax d={d} k={min(args.widths)}": ExpectimaxAgent(table, depth=d, width=min(args.widths))
                 for d in args.depths}
    optimum = [oracle.value(ids) for ids in small]
    report["small_sets"] = {"count": len(small), "mean_size": statistics.fmean(len(s) for s in small),
                            "optimum_mean": statistics.fmean(optimum), "policies": {}}
    print(f"\n{len(small)} small candidate sets (3-{args.max_small} words), optimum mean "
          f"{statistics.fmean(optimum):.4f}")
    for name, agent in policies.items():
        values = [policy_value(agent, table, ids) for ids in small]
        gaps = [v - o for v, o in zip(values, optimum)]
        entry = {"mean": statistics.fmean(values), "mean_gap": statistics.fmean(gaps), "max_gap": max(gaps),
                 "optimal_sets": sum(g < 1e-9 for g in gaps)}
        report["small_sets"]["policies"][name] = entry
        print(f"  {name:<20} mean {entry['mean']:.4f}  gap {entry['mean_gap']:.4f}  "
              f"optimal on {entry['optimal_sets']}/{len(small)}")

    # --- 3. exact optimum for fixed openers
    entropy_rank = [r["guess"] for r in make_agent("entropy", table=table).rank(all_ids, args.openers)]
    parts_rank = [r["guess"] for r in make_agent("most_parts", table=table).rank(all_ids, args.openers)]
    agent_openers = [r["results"][0].guesses[0] for r in reference.values()]
    agent_openers += [row["opener"] for row in report["grid"]]
    openers = list(dict.fromkeys(agent_openers + entropy_rank + parts_rank))
    expectimax_after = ExpectimaxAgent(table, depth=2, width=min(args.widths))
    entropy_agent = make_agent("entropy", table=table)
    report["openers"] = []
    print(f"\nexact optimum for {len(openers)} fixed openers:")
    for opener in openers:
        t0 = perf_counter()
        parts = split(table.matrix, table.guess_index[opener], all_ids)
        exact = 1.0 + sum(len(p) * oracle.value(p) for p in parts) / len(all_ids)
        seconds = perf_counter() - t0
        after_entropy = 1.0 + sum(len(p) * policy_value(entropy_agent, table, p) for p in parts) / len(all_ids)
        after_expectimax = 1.0 + sum(len(p) * policy_value(expectimax_after, table, p) for p in parts) / len(all_ids)
        report["openers"].append({"opener": opener, "exact": exact, "entropy_after": after_entropy,
                                  "expectimax_after": after_expectimax, "parts": len(parts),
                                  "is_answer": opener in table.answer_index, "seconds": seconds})
        print(f"  {to_upper(opener):<6} V* = {exact:.4f}  entropy after it {after_entropy:.4f}  "
              f"expectimax(2, {min(args.widths)}) after it {after_expectimax:.4f}  ({seconds:.1f} s)", flush=True)
    report["openers"].sort(key=lambda o: (o["exact"], o["opener"]))

    # --- 4. bounds on the optimum over all openers
    lower, lower_opener = opener_lower_bound(table)
    best = report["openers"][0]
    report["bounds"] = {"lower": lower, "lower_opener": lower_opener, "best_exact": best["exact"],
                        "best_exact_opener": best["opener"]}
    print(f"\noptimum over all openers: between {lower:.4f} (bound) and {best['exact']:.4f} "
          f"(exact with {to_upper(best['opener'])})")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "expectimax.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
    command = "python scripts/expectimax_study.py" + "".join(f" {a}" for a in sys.argv[1:])
    write_markdown(args.out_dir / "expectimax.md", report, command)
    print(f"wrote {args.out_dir / 'expectimax.json'} and expectimax.md")


def write_markdown(path: Path, report: dict, command: str) -> None:
    ref = report["reference"]
    lines = ["# Expectimax and oracle", "", f"Generated by `{command}`. Times are machine-dependent.", "",
             "## Cost table (all 1,900 answers, unlimited guesses)", "",
             f"Reference: entropy {ref['entropy']['mean']:.4f} ({to_upper(ref['entropy']['opener'])}), "
             f"most parts {ref['most_parts']['mean']:.4f} ({to_upper(ref['most_parts']['opener'])}).", "",
             "| Depth | Width | Mean guesses | Max | Opener | Value predicted at the opening | First move s "
             "| Total s | Nodes | Words better / worse than entropy |",
             "| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |"]
    for row in report["grid"]:
        lines.append(f"| {row['depth']} | {row['width']} | {row['mean']:.4f} | {row['max']} | "
                     f"{to_upper(row['opener'])} | {row['predicted_at_opening']:.4f} | {row['first_move_s']:.1f} | "
                     f"{row['total_s']:.1f} | {row['nodes']} | "
                     f"{row['words_better_than_entropy']} / {row['words_worse_than_entropy']} |")
    small = report["small_sets"]
    lines += ["", f"## Small candidate sets against the oracle ({small['count']} sets, mean size "
                  f"{small['mean_size']:.1f})", "",
              f"Exact optimum, mean over the sets: {small['optimum_mean']:.4f} guesses.", "",
              "| Policy | Mean guesses | Mean gap to optimum | Largest gap | Sets solved optimally |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for name, e in small["policies"].items():
        lines.append(f"| {name} | {e['mean']:.4f} | {e['mean_gap']:.4f} | {e['max_gap']:.4f} | "
                     f"{e['optimal_sets']} / {small['count']} |")
    lines += ["", "## Exact optimum for fixed openers", "",
              "V*(answers | opener) = 1 + the exact optimum of every part the opener leaves, weighted by size.", "",
              "| Opener | Is an answer | Parts | Exact optimum | Entropy agent after it | Expectimax after it | "
              "Seconds |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for o in report["openers"]:
        lines.append(f"| {to_upper(o['opener'])} | {'yes' if o['is_answer'] else 'no'} | {o['parts']} | "
                     f"{o['exact']:.4f} | {o['entropy_after']:.4f} | {o['expectimax_after']:.4f} | "
                     f"{o['seconds']:.1f} |")
    b = report["bounds"]
    lines += ["", "## Bounds on the optimum over all openers", "",
              f"* Lower bound (best one-step bound, opener {to_upper(b['lower_opener'])}): {b['lower']:.4f}",
              f"* Best exact value among the solved openers ({to_upper(b['best_exact_opener'])}): "
              f"{b['best_exact']:.4f}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
