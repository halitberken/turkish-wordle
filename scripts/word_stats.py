"""Word-list statistics: letter frequencies, repeated letters, best openers, one-letter families."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plot_style as ps  # noqa: E402

from wordle_tr import RESULTS_DIR  # noqa: E402
from wordle_tr.alphabet import to_upper  # noqa: E402
from wordle_tr.stats import TURKISH_SPECIFIC, word_statistics  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402


def plot_letter_frequency(stats: dict, path: Path) -> None:
    letters = [c for c, _ in stats["letters_by_presence"]]
    values = [v for _, v in stats["letters_by_presence"]]
    colors = [ps.SERIES[1] if c in TURKISH_SPECIFIC else ps.SERIES[0] for c in letters]
    xs = list(range(len(letters)))

    fig, ax = ps.new_figure(10, 4.6, rect=(0.06, 0.1, 0.92, 0.7))
    ax.set_xlim(-0.6, len(letters) - 0.4)
    ax.set_ylim(0, 60)
    ax.set_yticks(range(0, 61, 10))
    ax.set_yticklabels([f"{t}%" for t in range(0, 61, 10)])
    ax.set_xticks(xs)
    ax.set_xticklabels([to_upper(c) for c in letters], fontsize=10, color=ps.INK_SECONDARY)
    ps.rounded_bars(ax, xs, values, width=0.62, colors=colors)
    for x, c, v in zip(xs, letters, values):
        if c in TURKISH_SPECIFIC:
            ax.text(x, v + 1.2, f"{v:.1f}", ha="center", va="bottom", fontsize=7.5,
                    color=ps.INK_SECONDARY)
    ps.legend(ax, [("Also in the English alphabet", ps.SERIES[0]),
                   ("Turkish-specific letter (" + " ".join(to_upper(TURKISH_SPECIFIC)) + ")",
                    ps.SERIES[1])])
    ps.title(fig, "Share of answers containing each letter",
             f"{stats['answers']:,} answer words, letter counted once per word; "
             f"labels give the Turkish-specific letters' values (%)")
    ps.save(fig, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=10, help="rows in the opener / family tables")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="output folder")
    args = parser.parse_args()

    answers, guesses = load_answers(), load_guesses()
    stats = word_statistics(answers, guesses, top=args.top)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "word_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plot_letter_frequency(stats, args.out_dir / "letter_frequency.png")

    print(f"answers {stats['answers']:,}, guesses {stats['guesses']:,}")
    print("letters by presence in answers: " + ", ".join(
        f"{to_upper(c)} {v:.1f}%" for c, v in stats["letters_by_presence"][:10]) + ", …")
    print(f"answers with a repeated letter: {stats['answers_with_repeated_letter_pct']:.2f}%")
    print(f"answers with a Turkish-specific letter: "
          f"{stats['answers_with_turkish_specific_letter_pct']:.2f}%")
    print("best openers (answer list): " + ", ".join(
        f"{to_upper(r['word'])} {r['expected_letters_hit']:.3f}"
        for r in stats["best_openers_answers_only"][:5]))
    fam = stats["one_letter_families"]
    print(f"answers with a one-letter neighbour: {fam['answers_with_a_one_letter_neighbour_pct']:.2f}%;"
          f" largest family {to_upper(fam['largest'][0]['pattern'])} ({fam['largest'][0]['size']})")
    print(f"wrote {args.out_dir / 'word_stats.json'} and {args.out_dir / 'letter_frequency.png'}")


if __name__ == "__main__":
    main()
