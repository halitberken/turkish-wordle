"""Week 11 experiments: every agent on all answers (unlimited guesses), with bootstrap confidence
intervals, paired comparisons, ablations and an error analysis.

Writes <out-dir>/comparison.json, comparison.md, comparison_distribution.png,
comparison_cumulative.png and comparison_means.png. Times are machine-dependent;
everything else is deterministic (agents, seeds and resamples are fixed).
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

import plot_style as ps  # noqa: E402

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.agents import ExpectimaxAgent, default_table, make_agent  # noqa: E402
from wordle_tr.alphabet import sort_key, to_upper  # noqa: E402
from wordle_tr.analysis import (  # noqa: E402
    BUCKETS,
    bootstrap_ci,
    bootstrap_indices,
    family_bucket,
    paired_comparison,
    solved_by_turn,
)
from wordle_tr.feedback import pattern_to_emoji  # noqa: E402
from wordle_tr.filters import make_filter  # noqa: E402
from wordle_tr.simulate import evaluate, play_game  # noqa: E402
from wordle_tr.stats import one_letter_families  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402

AGENTS = ["random", "frequency", "entropy_candidates", "entropy", "entropy_freq", "most_parts", "expectimax"]
MAIN = ["random", "frequency", "entropy", "most_parts", "expectimax"]  # the line of the course, in the charts
LABELS = {"random": "random", "frequency": "letter frequency", "entropy_candidates": "entropy, candidates only",
          "entropy": "entropy", "entropy_freq": "entropy, frequency prior", "most_parts": "most parts",
          "expectimax": "expectimax (depth 2, width 10)"}
EXPECTIMAX_ABLATION = [(1, 10), (3, 10), (2, 25)]  # besides the main (2, 10)
LIMIT = 6


def run_agent(name: str, agent_factory, answers, guesses, filter_fn, seeds: list[int]) -> dict:
    """Play every answer; random agents once per seed (per-word guesses averaged over seeds)."""
    runs = []
    for seed in seeds:
        agent = agent_factory(seed)
        t0 = perf_counter()
        results = evaluate(agent, answers, guesses, filter_fn)
        runs.append({"seed": seed, "results": results, "seconds": perf_counter() - t0})
        if agent.deterministic:
            break
    per_run = np.array([[r.num_guesses for r in run["results"]] for run in runs], dtype=float)
    times = [t for run in runs for r in run["results"] for t in r.guess_times]
    return {
        "name": name,
        "runs": len(runs),
        "guesses": per_run.mean(axis=0),
        "per_run": per_run,
        "results": runs[0]["results"],
        "opener": runs[0]["results"][0].guesses[0],
        "ms_per_guess": 1000 * statistics.fmean(times),
        "seconds_per_run": statistics.fmean(run["seconds"] for run in runs),
    }


def summary_row(run: dict, indices: np.ndarray) -> dict:
    per_run = run["per_run"]
    low, high = bootstrap_ci(run["guesses"], indices)
    return {
        "agent": run["name"],
        "runs": run["runs"],
        "opener": run["opener"],
        "mean": float(run["guesses"].mean()),
        "ci_low": low,
        "ci_high": high,
        "within_6_pct": float(100 * (per_run <= LIMIT).mean()),
        "failures": float((per_run > LIMIT).sum(axis=1).mean()),
        "max": int(per_run.max()),
        "ms_per_guess": run["ms_per_guess"],
        "seconds": run["seconds_per_run"],
    }


def game_record(agent, word: str, answers, guesses, filter_fn) -> list[dict]:
    turns = []

    def on_turn(turn: int, guess: str, pattern: int, candidates: list[str]) -> None:
        turns.append({"guess": guess, "pattern": pattern_to_emoji(pattern), "left": len(candidates),
                      "candidates": candidates if len(candidates) <= 12 else []})

    play_game(agent, word, answers, guesses, filter_fn, None, on_turn)
    return turns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5, help="runs of the random agent (seeds 0..N-1)")
    parser.add_argument("--resamples", type=int, default=10_000, help="bootstrap resamples (default 10,000)")
    parser.add_argument("--permutations", type=int, default=10_000, help="sign-flip permutations (default 10,000)")
    parser.add_argument("--seed", type=int, default=1234, help="seed for resampling and permutations")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="output folder")
    args = parser.parse_args()

    answers, guesses = load_answers(), load_guesses()
    table = default_table()
    filter_fn = make_filter("table", answers, guesses, table)
    indices = bootstrap_indices(len(answers), args.resamples, args.seed)

    # --- run everything
    runs: dict[str, dict] = {}
    for name in AGENTS:
        runs[name] = run_agent(name, lambda seed, n=name: make_agent(n, seed, table=table), answers, guesses,
                               filter_fn, list(range(args.seeds)))
        print(f"{name:<19} mean {runs[name]['guesses'].mean():.4f}  ({runs[name]['seconds_per_run']:.1f} s per run)",
              flush=True)
    for depth, width in EXPECTIMAX_ABLATION:
        key = f"expectimax d={depth} k={width}"
        runs[key] = run_agent(key, lambda seed, d=depth, w=width: ExpectimaxAgent(table, depth=d, width=w),
                              answers, guesses, filter_fn, [0])
        print(f"{key:<19} mean {runs[key]['guesses'].mean():.4f}  ({runs[key]['seconds_per_run']:.1f} s)", flush=True)
    runs["expectimax d=2 k=10"] = runs["expectimax"]

    rows = {name: summary_row(runs[name], indices) for name in AGENTS}
    ablation_rows = {key: summary_row(runs[key], indices)
                     for key in ["expectimax d=1 k=10", "expectimax d=2 k=10", "expectimax d=3 k=10",
                                 "expectimax d=2 k=25"]}
    max_turn = max(int(r["per_run"].max()) for r in runs.values())

    # --- paired comparisons
    def compare(a: str, b: str, seed_offset: int) -> dict:
        result = paired_comparison(runs[a]["guesses"], runs[b]["guesses"], indices, args.permutations,
                                   args.seed + seed_offset)
        return {"a": a, "b": b, **result}

    chain = [compare(a, b, i) for i, (a, b) in enumerate(zip(MAIN, MAIN[1:]))]
    ablations = [
        ("candidates only vs full guess list", compare("entropy_candidates", "entropy", 10)),
        ("frequency prior vs uniform prior", compare("entropy_freq", "entropy", 11)),
        ("expectimax depth 1 vs depth 2 (width 10)", compare("expectimax d=1 k=10", "expectimax d=2 k=10", 12)),
        ("expectimax depth 2 vs depth 3 (width 10)", compare("expectimax d=2 k=10", "expectimax d=3 k=10", 13)),
        ("expectimax width 10 vs width 25 (depth 2)", compare("expectimax d=2 k=10", "expectimax d=2 k=25", 14)),
    ]

    # --- error analysis
    family: dict[str, tuple[str, int]] = {w: ("", 1) for w in answers}
    for pattern, members in one_letter_families(answers):
        for w in members:
            if len(members) > family[w][1]:
                family[w] = (pattern, len(members))
    buckets = {b: [i for i, w in enumerate(answers) if family_bucket(family[w][1]) == b] for b in BUCKETS}
    bucket_table = {b: {"words": len(ids), **{name: float(runs[name]["guesses"][ids].mean()) for name in MAIN}}
                    for b, ids in buckets.items()}
    hardest = {}
    for name in AGENTS:
        order = sorted(range(len(answers)), key=lambda i: (-runs[name]["guesses"][i], sort_key(answers[i])))[:10]
        hardest[name] = [{"word": answers[i], "guesses": float(runs[name]["guesses"][i]),
                          "family": family[answers[i]][0], "family_size": family[answers[i]][1]} for i in order]
    search = ["entropy", "most_parts", "expectimax"]
    worst = max(int(runs[name]["guesses"].max()) for name in search)
    hard_for_all = [w for i, w in enumerate(answers) if all(runs[n]["guesses"][i] >= worst for n in search)]
    expectimax_max = int(runs["expectimax"]["guesses"].max())
    example = next(w for i, w in enumerate(answers) if runs["expectimax"]["guesses"][i] == expectimax_max
                   and family[w][1] >= 3)
    example_games = {name: game_record(make_agent(name, table=table), example, answers, guesses, filter_fn)
                     for name in ["frequency", "entropy", "most_parts", "expectimax"]}

    report = {
        "config": {"answers": len(answers), "guesses": len(guesses), "filter": "table", "seeds": args.seeds,
                   "resamples": args.resamples, "permutations": args.permutations, "seed": args.seed,
                   "limit": LIMIT},
        "agents": rows,
        "expectimax_ablation": ablation_rows,
        "distribution": {name: {str(k): float((runs[name]["per_run"] == k).sum() / runs[name]["runs"])
                                for k in range(1, max_turn + 1)} for name in AGENTS},
        "solved_by_turn": {name: solved_by_turn(runs[name]["per_run"].ravel(), max_turn) for name in AGENTS},
        "paired_chain": chain,
        "paired_ablations": [{"question": q, **c} for q, c in ablations],
        "buckets": bucket_table,
        "hardest": hardest,
        "hard_for_all_search_agents": {"guesses": worst, "words": hard_for_all},
        "example": {"word": example, "family": family[example][0], "family_size": family[example][1],
                    "games": example_games},
        "words": answers,
        "guesses_per_word": {name: runs[name]["guesses"].tolist() for name in runs},
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
    command = "python scripts/experiments.py" + "".join(f" {a}" for a in sys.argv[1:])
    write_markdown(args.out_dir / "comparison.md", report, command)
    plot_distribution(args.out_dir / "comparison_distribution.png", report, max_turn)
    plot_cumulative(args.out_dir / "comparison_cumulative.png", report, max_turn)
    plot_means(args.out_dir / "comparison_means.png", report)

    print("\nagent                     mean   95% CI              within 6   max")
    for name, r in rows.items():
        print(f"{name:<22} {r['mean']:.4f}  [{r['ci_low']:.4f}, {r['ci_high']:.4f}]  {r['within_6_pct']:7.2f}  "
              f"{r['max']:4d}")
    print("\npaired (positive = second agent needs fewer guesses)")
    for c in chain + [c for _, c in ablations]:
        print(f"  {c['a']:<20} -> {c['b']:<20} {c['mean_difference']:+.4f} "
              f"[{c['ci_low']:+.4f}, {c['ci_high']:+.4f}]  p = {c['p_value']:.4f}")
    print(f"\nwrote {args.out_dir / 'comparison.json'}, comparison.md and three charts")


def fmt_ci(r: dict) -> str:
    return f"{r['mean']:.4f} [{r['ci_low']:.4f}, {r['ci_high']:.4f}]"


def write_markdown(path: Path, report: dict, command: str) -> None:
    cfg = report["config"]
    lines = [
        "# Agent comparison", "",
        f"Generated by `{command}`. All {cfg['answers']:,} answers, unlimited guesses, `table` filter. "
        f"95 % confidence intervals: bootstrap over the words ({cfg['resamples']:,} resamples, seed {cfg['seed']}). "
        f"The random agent is run with {cfg['seeds']} seeds; its per-word guesses are averaged over the seeds. "
        "Times are machine-dependent.", "",
        "| Agent | Opener | Mean [95 % CI] | % solved ≤ 6 | Failures (> 6) | Max | ms / guess | Total s |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in report["agents"].items():
        opener = to_upper(r["opener"]) + (" (seed 0)" if r["runs"] > 1 else "")
        fails = f"{r['failures']:.1f}" if r["runs"] > 1 else f"{r['failures']:.0f}"
        lines.append(f"| {LABELS[name]} | {opener} | {fmt_ci(r)} | {r['within_6_pct']:.2f} | {fails} | {r['max']} | "
                     f"{r['ms_per_guess']:.3f} | {r['seconds']:.1f} |")
    lines += ["", "## Expectimax depth and width", "",
              "| Configuration | Mean [95 % CI] | Max | ms / guess | Total s |", "| --- | --- | ---: | ---: | ---: |"]
    for key, r in report["expectimax_ablation"].items():
        lines.append(f"| {key} | {fmt_ci(r)} | {r['max']} | {r['ms_per_guess']:.3f} | {r['seconds']:.1f} |")

    dist = report["distribution"]
    turns = sorted({int(k) for d in dist.values() for k in d})
    lines += ["", "## Guess-count distribution (words)", "",
              "| Guesses | " + " | ".join(LABELS[n] for n in dist) + " |",
              "| ---: | " + " | ".join("---:" for _ in dist) + " |"]
    for t in turns:
        lines.append(f"| {t} | " + " | ".join(
            f"{dist[n][str(t)]:.1f}" if report["agents"][n]["runs"] > 1 else f"{dist[n][str(t)]:.0f}" for n in dist)
            + " |")
    lines += ["", "## Solved within t guesses (%)", "",
              "| Agent | " + " | ".join(f"t = {t}" for t in turns) + " |",
              "| --- | " + " | ".join("---:" for _ in turns) + " |"]
    for name, values in report["solved_by_turn"].items():
        lines.append(f"| {LABELS[name]} | " + " | ".join(f"{v:.2f}" for v in values) + " |")

    lines += ["", "## Paired comparisons", "",
              "Difference = mean guesses of the first agent minus the second, on the same words "
              "(positive: the second is better). CI: bootstrap; p: sign-flip permutation test "
              f"({cfg['permutations']:,} permutations).", "",
              "| Comparison | Mean difference [95 % CI] | Second better / worse / equal | p |",
              "| --- | --- | --- | ---: |"]
    pairs = [(f"{LABELS[c['a']]} → {LABELS[c['b']]}", c) for c in report["paired_chain"]]
    pairs += [(c["question"], c) for c in report["paired_ablations"]]
    for label, c in pairs:
        lines.append(f"| {label} | {c['mean_difference']:+.4f} [{c['ci_low']:+.4f}, {c['ci_high']:+.4f}] | "
                     f"{c['b_better']} / {c['b_worse']} / {c['equal']} | {c['p_value']:.4f} |")

    lines += ["", "## Difficulty by one-letter family", "",
              "Words grouped by the size of their largest one-letter family (week 6); mean guesses per agent.", "",
              "| Group | Words | " + " | ".join(LABELS[n] for n in MAIN) + " |",
              "| --- | ---: | " + " | ".join("---:" for _ in MAIN) + " |"]
    for bucket, row in report["buckets"].items():
        lines.append(f"| {bucket} | {row['words']} | " + " | ".join(f"{row[n]:.4f}" for n in MAIN) + " |")

    lines += ["", "## Hardest words per agent", ""]
    for name, words in report["hardest"].items():
        cells = []
        for item in words:
            g = f"{item['guesses']:.1f}" if report["agents"][name]["runs"] > 1 else f"{item['guesses']:.0f}"
            fam = f", {to_upper(item['family'])}" if item["family"] else ""
            cells.append(f"{to_upper(item['word'])} {g}{fam}")
        lines.append(f"* **{LABELS[name]}**: " + "; ".join(cells))
    hard = report["hard_for_all_search_agents"]
    lines += ["", f"Words that need {hard['guesses']} guesses with entropy, most parts **and** expectimax: "
              + (", ".join(to_upper(w) for w in hard["words"]) or "none") + "."]

    ex = report["example"]
    lines += ["", f"## Example: {to_upper(ex['word'])} (one-letter family {to_upper(ex['family'])}, "
                  f"{ex['family_size']} words)", ""]
    for name, turns_ in ex["games"].items():
        lines += [f"**{LABELS[name]}**: {len(turns_)} guesses", "", "```text"]
        for i, t in enumerate(turns_, 1):
            left = "" if t["pattern"] == "🟩🟩🟩🟩🟩" else f"  {t['left']} left"
            if t["candidates"] and t["pattern"] != "🟩🟩🟩🟩🟩":
                left += ": " + ", ".join(to_upper(w) for w in t["candidates"])
            lines.append(f"{i}. {to_upper(t['guess'])} {t['pattern']}{left}")
        lines += ["```", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


COLORS = {name: ps.SERIES[i] for i, name in enumerate(MAIN)}  # colour follows the agent in every chart


def plot_distribution(path: Path, report: dict, max_turn: int) -> None:
    turns = list(range(1, max_turn + 1))
    words = report["config"]["answers"]
    width = 0.15
    fig, ax = ps.new_figure(9, 4.6, rect=(0.07, 0.1, 0.9, 0.68))
    shares = {n: [100 * report["distribution"][n][str(t)] / words for t in turns] for n in MAIN}
    top = max(max(v) for v in shares.values())
    ax.set_xlim(0.4, len(turns) + 0.6)
    ax.set_ylim(0, (int(top / 10) + 1) * 10)
    ax.axvspan(LIMIT + 0.5, len(turns) + 0.6, color=ps.GRID, alpha=0.45, linewidth=0, zorder=0)
    ax.text(LIMIT + 0.6, ax.get_ylim()[1] * 0.97, f"not solved within {LIMIT}", fontsize=8.5,
            color=ps.INK_SECONDARY, va="top")
    ax.set_xticks(turns)
    ax.set_xticklabels([str(t) for t in turns], color=ps.INK_SECONDARY)
    ax.set_xlabel("guesses needed", color=ps.INK_MUTED, fontsize=9)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    for j, name in enumerate(MAIN):
        offset = (j - (len(MAIN) - 1) / 2) * (width + 0.02)
        ps.rounded_bars(ax, [t + offset for t in turns], shares[name], width, [COLORS[name]] * len(turns))
    ps.legend(ax, [(f"{LABELS[n]} ({report['agents'][n]['mean']:.4f})", COLORS[n]) for n in MAIN],
              loc="upper right", anchor=(1.0, 0.9))
    ps.title(fig, "How many guesses each agent needs",
             f"share of the {words:,} answers (random agent: mean of {report['config']['seeds']} seeds)")
    ps.save(fig, path)


def plot_cumulative(path: Path, report: dict, max_turn: int) -> None:
    turns = list(range(1, max_turn + 1))
    fig, ax = ps.new_figure(9, 4.6, rect=(0.07, 0.1, 0.62, 0.68))
    ax.set_xlim(0.7, max_turn + 0.3)
    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xticks(turns)
    ax.set_xticklabels([str(t) for t in turns], color=ps.INK_SECONDARY)
    ax.set_xlabel("guesses allowed (t)", color=ps.INK_MUTED, fontsize=9)
    ax.axvline(LIMIT, color=ps.BASELINE, linewidth=1, zorder=1)
    ax.text(LIMIT + 0.08, 4, "game limit", fontsize=8, color=ps.INK_MUTED)
    for name in MAIN:
        values = report["solved_by_turn"][name]
        ax.plot(turns, values, color=COLORS[name], linewidth=2, solid_capstyle="round", zorder=3)
        ax.scatter(turns, values, s=36, color=COLORS[name], edgecolors=ps.SURFACE, linewidths=1.5, zorder=4)
    ps.legend(ax, [(LABELS[n], COLORS[n]) for n in MAIN], loc="center left", anchor=(1.02, 0.5))
    ps.title(fig, "Share of answers solved within t guesses", "all 1,900 answers, unlimited guesses")
    ps.save(fig, path)


def plot_means(path: Path, report: dict) -> None:
    import matplotlib.pyplot as plt  # noqa: F401  (plot_style already configured the backend)

    rows = sorted(report["agents"].items(), key=lambda item: -item[1]["mean"])
    fig, ax = ps.new_figure(9, 4.2, rect=(0.27, 0.12, 0.66, 0.66))
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=ps.GRID, linewidth=0.8)
    ys = list(range(len(rows)))
    for y, (name, r) in zip(ys, rows):
        ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=ps.SERIES[0], linewidth=2, solid_capstyle="round")
        ax.scatter([r["mean"]], [y], s=48, color=ps.SERIES[0], edgecolors=ps.SURFACE, linewidths=1.5, zorder=3)
        ax.text(r["ci_high"] + 0.012, y, f"{r['mean']:.3f}", va="center", fontsize=8.5, color=ps.INK_SECONDARY)
    ax.set_yticks(ys)
    ax.set_yticklabels([LABELS[name] for name, _ in rows], color=ps.INK_SECONDARY, fontsize=9)
    low = min(r["ci_low"] for _, r in rows)
    high = max(r["ci_high"] for _, r in rows)
    ax.set_xlim(low - 0.05, high + 0.12)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("mean guesses (dot) with 95 % bootstrap interval", color=ps.INK_MUTED, fontsize=9)
    ps.title(fig, "Mean number of guesses per agent", "all 1,900 answers; lower is better")
    ps.save(fig, path)


if __name__ == "__main__":
    main()
