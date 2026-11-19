"""Examples for the week 9 report: best openers by entropy, a worked example on a small
candidate set, and how the entropy agents play the words the letter-frequency agent loses.

Writes <out-dir>/entropy_examples.json and entropy_examples.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.agents import default_table, make_agent  # noqa: E402
from wordle_tr.alphabet import to_upper  # noqa: E402
from wordle_tr.feedback import feedback, pattern_to_emoji  # noqa: E402
from wordle_tr.filters import make_filter  # noqa: E402
from wordle_tr.simulate import evaluate, play_game  # noqa: E402
from wordle_tr.agents.entropy import entropy_bits  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402

VARIANTS = ["entropy", "entropy_candidates", "entropy_freq", "most_parts"]
EXAMPLE_WORD = "sayma"


def partition(guess: str, candidates: list[str]) -> dict:
    parts: dict[int, list[str]] = defaultdict(list)
    for word in candidates:
        parts[feedback(guess, word)].append(word)
    sizes = [len(words) for words in parts.values()]
    return {
        "guess": guess,
        "is_candidate": guess in candidates,
        "parts": [{"pattern": pattern_to_emoji(p), "words": words}
                  for p, words in sorted(parts.items(), key=lambda item: (-len(item[1]), item[0]))],
        "sizes": sorted(sizes, reverse=True),
        "bits": entropy_bits(sizes),
    }


def game_record(agent_name: str, word: str, answers, guesses, filter_fn, table) -> dict:
    agent = make_agent(agent_name, table=table)
    turns = []

    def on_turn(turn: int, guess: str, pattern: int, candidates: list[str]) -> None:
        info = getattr(agent, "last_choice", None)
        turns.append({"guess": guess, "pattern": pattern_to_emoji(pattern),
                      "bits": info["bits"] if info else None,
                      "is_candidate": info["is_candidate"] if info else True,
                      "candidates_left": len(candidates),
                      "remaining": candidates if len(candidates) <= 8 else []})

    result = play_game(agent, word, answers, guesses, filter_fn, None, on_turn)
    return {"agent": agent_name, "answer": word, "guesses": result.num_guesses, "turns": turns}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10, help="openers listed per agent (default 10)")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="output folder")
    args = parser.parse_args()

    answers, guesses = load_answers(), load_guesses()
    table = default_table()
    filter_fn = make_filter("table", answers, guesses, table)
    report: dict = {}

    # 1. best openers
    report["openers"] = {}
    for name in VARIANTS:
        agent = make_agent(name, table=table)
        report["openers"][name] = agent.rank(table.all_ids(), args.top)
        best = report["openers"][name][0]
        print(f"{name:<19} opener {to_upper(best['guess'])} {best['bits']:.4f} bits, {best['parts']} parts")

    # 2. worked example: the letter-frequency agent's position after three guesses for SAYMA
    frequency_game = game_record("frequency", EXAMPLE_WORD, answers, guesses, filter_fn, table)
    state = next(t for t in frequency_game["turns"] if t["candidates_left"] <= 8 and t["remaining"])
    history_length = frequency_game["turns"].index(state) + 1
    candidates = state["remaining"]
    entropy_agent = make_agent("entropy", table=table)
    entropy_choice = entropy_agent.rank(table.answer_ids(candidates), 1)[0]["guess"]
    candidate_choice = make_agent("entropy_candidates", table=table).rank(table.answer_ids(candidates), 1)[0]["guess"]
    frequency_choice = frequency_game["turns"][history_length]["guess"]
    report["worked_example"] = {
        "history": [{"guess": t["guess"], "pattern": t["pattern"]} for t in frequency_game["turns"][:history_length]],
        "candidates": candidates,
        "guesses": [partition(g, candidates) for g in dict.fromkeys([frequency_choice, candidate_choice,
                                                                     entropy_choice])],
    }
    print(f"\nworked example: {len(candidates)} candidates {', '.join(map(to_upper, candidates))}")
    for item in report["worked_example"]["guesses"]:
        print(f"  {to_upper(item['guess'])}: sizes {item['sizes']} -> {item['bits']:.4f} bits")

    # 3. the words the letter-frequency agent loses, played by every agent
    frequency_results = evaluate(make_agent("frequency"), answers, guesses, filter_fn)
    lost = [r.answer for r in frequency_results if r.num_guesses > 6]
    agents = ["frequency"] + VARIANTS
    played = {name: {r.answer: r.num_guesses for r in evaluate(make_agent(name, table=table), answers, guesses,
                                                                filter_fn, words=lost)} for name in agents}
    report["frequency_failures"] = {"words": lost, "guesses": played}
    report["games"] = {name: game_record(name, EXAMPLE_WORD, answers, guesses, filter_fn, table)
                       for name in agents}
    print(f"\nthe {len(lost)} words the frequency agent needs more than 6 guesses for:")
    for name in agents:
        print(f"  {name:<19} max {max(played[name].values())}, total {sum(played[name].values())}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "entropy_examples.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_markdown(args.out_dir / "entropy_examples.md", report)
    print(f"\nwrote {args.out_dir / 'entropy_examples.json'} and entropy_examples.md")


def write_markdown(path: Path, report: dict) -> None:
    lines = ["# Entropy agent examples", "", "Generated by `python scripts/entropy_examples.py`.", "",
             "## Best openers (all 1,900 answers are candidates)", ""]
    for name, rows in report["openers"].items():
        lines += [f"### {name}", "", "| Rank | Guess | Entropy (bits) | Parts | Is an answer |",
                  "| ---: | --- | ---: | ---: | --- |"]
        for i, r in enumerate(rows, 1):
            lines.append(f"| {i} | {to_upper(r['guess'])} | {r['bits']:.4f} | {r['parts']} | "
                         f"{'yes' if r['is_candidate'] else 'no'} |")
        lines.append("")

    ex = report["worked_example"]
    lines += ["## Worked example", "",
              "Position of the letter-frequency agent in the SAYMA game after "
              + ", ".join(f"{to_upper(h['guess'])} {h['pattern']}" for h in ex["history"]) + ": "
              + f"{len(ex['candidates'])} candidates ({', '.join(map(to_upper, ex['candidates']))}).", ""]
    for item in ex["guesses"]:
        kind = "a candidate" if item["is_candidate"] else "not a candidate"
        lines += [f"**{to_upper(item['guess'])}** ({kind}): part sizes {item['sizes']}, "
                  f"H = {item['bits']:.4f} bits", ""]
        for part in item["parts"]:
            lines.append(f"* {part['pattern']}: {', '.join(map(to_upper, part['words']))}")
        lines.append("")

    fails = report["frequency_failures"]
    names = list(fails["guesses"])
    lines += ["## The words the letter-frequency agent needs more than 6 guesses for", "",
              "| Word | " + " | ".join(names) + " |", "| --- | " + " | ".join("---:" for _ in names) + " |"]
    for word in fails["words"]:
        lines.append(f"| {to_upper(word)} | " + " | ".join(str(fails["guesses"][n][word]) for n in names) + " |")
    lines.append("| **max** | " + " | ".join(str(max(fails["guesses"][n].values())) for n in names) + " |")

    lines += ["", f"## {to_upper(EXAMPLE_WORD)}, played by every agent", ""]
    for name, game in report["games"].items():
        lines += [f"**{name}**: {game['guesses']} guesses", "", "```text"]
        for i, t in enumerate(game["turns"], 1):
            bits = f"{t['bits']:5.2f} bits" if t["bits"] is not None else " " * 10
            left = "" if t["pattern"] == "🟩🟩🟩🟩🟩" else f"  {t['candidates_left']} left"
            if t["remaining"] and t["pattern"] != "🟩🟩🟩🟩🟩":
                left += ": " + ", ".join(map(to_upper, t["remaining"]))
            lines.append(f"{i}. {to_upper(t['guess'])} {t['pattern']} {bits}{left}")
        lines += ["```", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
