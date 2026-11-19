"""Export the data the web demo needs to web/public/data/.

* guesses.json, answers.json: the word lists (lower case, Turkish order);
* openers.json: each browser agent's first guess, and the entropy agent's second
  guess for every pattern of its first guess (so turn 2 is instant);
* feedback_fixtures.json: duplicate-letter cases, random (guess, answer, pattern)
  triples, and Constraints.describe() texts, to test the TypeScript port;
* agent_fixtures.json: full games of the frequency and entropy agents on a sample;
* summary.json: headline results for the "How it works" page.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.agents import default_table, make_agent  # noqa: E402
from wordle_tr.alphabet import normalize  # noqa: E402
from wordle_tr.constraints import Constraints, ContradictionError  # noqa: E402
from wordle_tr.feedback import feedback, parse_pattern, pattern_to_emoji  # noqa: E402
from wordle_tr.filters import make_filter  # noqa: E402
from wordle_tr.simulate import evaluate, random_histories  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402

DUPLICATE_CASES = [  # (guess, answer) pairs from tests/test_feedback.py
    ("KAPAK", "KALEM"), ("EKLER", "KALEM"), ("TATLI", "OTLAK"), ("KEKİK", "KAYAK"), ("KALEM", "KALEM"),
    ("ÜZGÜN", "KALEM"), ("AAAAA", "KAPAK"), ("ALAKA", "KAPAK"), ("SAYMA", "SAÇMA"), ("ILGIN", "İLGİN"),
]
CONTRADICTIONS = [  # histories that Constraints rejects (tests/test_week8.py)
    [("kapak", "gxxyx")],
    [("kalem", "ggggg"), ("kalem", "xxxxx")],
    [("kalem", "gxxxx"), ("sayma", "gxxxx")],
    [("aaaaa", "yyyyy")],
    [("kalem", "yyyyy"), ("erika", "xxxxx")],
]


def write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "web" / "public" / "data", help="output folder")
    parser.add_argument("--triples", type=int, default=2000, help="random feedback triples (default 2000)")
    parser.add_argument("--games", type=int, default=300, help="sample words for agent games (default 300)")
    parser.add_argument("--seed", type=int, default=1234, help="seed for the random samples (default 1234)")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    answers, guesses = load_answers(), load_guesses()
    table = default_table()
    rng = random.Random(args.seed)

    write(args.out_dir / "guesses.json", guesses)
    write(args.out_dir / "answers.json", answers)

    # openers: first guesses, and the entropy agent's second guess for every first pattern
    entropy = make_agent("entropy", table=table)
    first = entropy.choose_guess([], answers)
    opening = entropy.last_choice
    second = {}
    for pattern in sorted({feedback(first, w) for w in answers}):
        candidates = [w for w in answers if feedback(first, w) == pattern]
        guess = entropy.choose_guess([(first, pattern)], candidates)
        second[str(pattern)] = {"guess": guess, "bits": round(entropy.last_choice["bits"], 6),
                                "candidates": len(candidates)}
    openers = {
        "frequency": {"first": make_agent("frequency").choose_guess([], answers)},
        "entropy": {"first": first, "bits": round(opening["bits"], 6), "second": second},
    }
    write(args.out_dir / "openers.json", openers)

    # feedback fixtures
    cases = [{"guess": normalize(g), "answer": normalize(a), "pattern": feedback(normalize(g), normalize(a)),
              "emoji": pattern_to_emoji(feedback(normalize(g), normalize(a)))} for g, a in DUPLICATE_CASES]
    triples = []
    for _ in range(args.triples):
        g, a = rng.choice(guesses), rng.choice(answers)
        triples.append([g, a, feedback(g, a)])
    describe = [{"history": [[g, p] for g, p in history], "text": Constraints.from_history(history).describe()}
                for _, history in random_histories(answers, guesses, 60, args.seed)]
    for guess, answer in [("kapak", "kalem"), ("ekler", "kalem"), ("tatlı", "otlak"), ("kalem", "kayak")]:
        history = [(guess, feedback(guess, answer))]
        describe.append({"history": [[guess, history[0][1]]], "text": Constraints.from_history(history).describe()})
    contradictions = []
    for history in CONTRADICTIONS:
        parsed = [(g, parse_pattern(p)) for g, p in history]
        try:
            Constraints.from_history(parsed)
        except ContradictionError:
            contradictions.append([[g, p] for g, p in parsed])
    write(args.out_dir / "feedback_fixtures.json",
          {"cases": cases, "triples": triples, "describe": describe, "contradictions": contradictions})

    # agent games on a sample of words
    sample = sorted(rng.sample(range(len(answers)), args.games))
    words = [answers[i] for i in sample]
    filter_fn = make_filter("table", answers, guesses, table)
    games = {name: [r.guesses for r in evaluate(make_agent(name, table=table), answers, guesses, filter_fn,
                                                 words=words)] for name in ("frequency", "entropy")}
    write(args.out_dir / "agent_fixtures.json", {"words": words, "games": games})

    # headline results
    comparison = json.loads((RESULTS_DIR / "comparison.json").read_text(encoding="utf-8"))
    bounds = json.loads((RESULTS_DIR / "expectimax.json").read_text(encoding="utf-8"))["bounds"]
    labels = {"random": "Random", "frequency": "Letter frequency", "entropy_candidates": "Entropy, candidates only",
              "entropy": "Entropy", "entropy_freq": "Entropy, frequency prior", "most_parts": "Most parts",
              "expectimax": "Expectimax (depth 2, width 10)"}
    summary = {
        "answers": len(answers),
        "guesses": len(guesses),
        "agents": [{"name": name, "label": labels[name], "opener": row["opener"], "mean": round(row["mean"], 4),
                    "ci": [round(row["ci_low"], 4), round(row["ci_high"], 4)],
                    "within6": round(row["within_6_pct"], 2), "max": row["max"]}
                   for name, row in comparison["agents"].items()],
        "optimum": {"lower": round(bounds["lower"], 4), "best": round(bounds["best_exact"], 4),
                    "opener": bounds["best_exact_opener"]},
    }
    write(args.out_dir / "summary.json", summary)

    sizes = {p.name: p.stat().st_size for p in sorted(args.out_dir.glob("*.json"))}
    for name, size in sizes.items():
        print(f"{name:<24} {size / 1024:7.1f} KB")
    print(f"entropy opener {first.upper()} with {len(second)} second guesses; "
          f"{len(triples)} feedback triples; {len(words)} agent games per agent")


if __name__ == "__main__":
    main()
