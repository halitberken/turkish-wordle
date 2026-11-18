"""Build data/guesses.txt, data/answers.txt and data/frequencies.tsv from data/raw/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_tr import RESULTS_DIR, words  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=words.DATA_DIR,
                        help="folder with raw/ and excluded_answers.txt; outputs are written here")
    parser.add_argument("--results", type=Path, default=RESULTS_DIR / "word_lists.json",
                        help="where to write the step counts (JSON)")
    args = parser.parse_args()

    raw = args.data_dir / "raw"
    build = words.build_word_lists(
        dictionary_paths=(raw / "tdk_cannuhlar.txt", raw / "tdk_mertemin.txt"),
        subtitle_path=raw / "opensubtitles_tr_50k.txt",
        excluded_path=args.data_dir / "excluded_answers.txt",
    )

    for name, info in build.details["sources"].items():
        print(f"{name:<28} {info['entries']:>7,} entries  sha256 {info['sha256'][:16]}…")
    print()
    for step, count in build.steps:
        print(f"{count:>7,}  {step}")
    print(f"\nexcluded answers: {', '.join(build.excluded)}")

    n_guesses, n_answers = len(build.guesses), len(build.answers)
    words.write_word_file(
        args.data_dir / "guesses.txt", build.guesses,
        f"{n_guesses} valid 5-letter Turkish guesses (TDK lists), Turkish order; "
        "built by scripts/build_word_lists.py")
    words.write_word_file(
        args.data_dir / "answers.txt", build.answers,
        f"{n_answers} possible answers (guesses also in the 50k subtitle list, minus "
        "excluded_answers.txt), Turkish order; built by scripts/build_word_lists.py")
    words.write_frequencies(
        args.data_dir / "frequencies.tsv", build.frequencies,
        "word<TAB>subtitle_count for every answer (OpenSubtitles 2018 tr_50k, spellings "
        "merged after normalisation); built by scripts/build_word_lists.py")

    args.results.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "steps": [{"step": step, "count": count} for step, count in build.steps],
        "guesses": n_guesses,
        "answers": n_answers,
        **build.details,
    }
    args.results.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote guesses.txt ({n_guesses}), answers.txt ({n_answers}) and frequencies.tsv "
          f"to {args.data_dir}; step counts to {args.results}")


if __name__ == "__main__":
    main()
