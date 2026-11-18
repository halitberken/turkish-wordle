# Turkish Wordle Solver

Term project for **BIL 4112 Artificial Intelligence**, Dokuz Eylül University.
Team: Berken (lead), Arda, Faruk.

AI agents that find a hidden 5-letter **Turkish** word in as few guesses as
possible. The project compares constraint-based candidate filtering (CSP),
information theory (entropy) and expectimax search fairly and reproducibly,
and ends with a playable web demo.

## Status

| Week | Topic | Owner | Status |
| --- | --- | --- | --- |
| 6 | Problem definition, Turkish alphabet, word lists, statistics, literature | Faruk | ✅ done: [doc](docs/week6_problem_and_literature.md) |
| 7 | Feedback, game, agent interface, baselines, evaluation | Arda | ⏳ next |
| 8 | Constraints, CSP solver, pattern table, filter benchmark | Berken | – |
| 9 | Entropy (information-gain) agent | Arda | – |
| 10 | Expectimax search and oracle | Berken | – |
| 11 | Experiments and analysis | Faruk | – |
| 12 | Final report, presentation, hand-in | everyone | – |
| – | Playable web demo (GitHub Pages) | – | – |

## Setup

Python ≥ 3.10.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt     # numpy (runtime), matplotlib + pytest (dev)
python -m pytest                    # slow tests are skipped; add --runslow to include them
```

## Usage

| Command | What it does |
| --- | --- |
| `python scripts/build_word_lists.py` | Builds `data/guesses.txt`, `data/answers.txt`, `data/frequencies.tsv` from `data/raw/`; step counts → `results/word_lists.json` |
| `python scripts/word_stats.py` | Letter frequencies, repeated letters, best openers, one-letter families → `results/word_stats.json`, `results/letter_frequency.png` |

Every script has `--help`.

## Word lists

The pipeline counts are in [`results/word_lists.json`](results/word_lists.json).

| List | Words | Definition |
| --- | ---: | --- |
| Guesses `data/guesses.txt` | 5,370 | 5-letter lower-case entries of two TDK dictionary lists (no proper nouns, no multi-word entries, circumflexes removed) |
| Answers `data/answers.txt` | 1,900 | Guesses that also appear in the 50k OpenSubtitles frequency list, minus 7 offensive words (`data/excluded_answers.txt`) |

Data sources (copied into `data/raw/`):
[CanNuhlar/Turkce-Kelime-Listesi](https://github.com/CanNuhlar/Turkce-Kelime-Listesi),
[mertemin/turkish-word-list](https://github.com/mertemin/turkish-word-list),
[hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) (`content/2018/tr/tr_50k.txt`).

## Repository layout

```
wordle_tr/       importable package
  alphabet.py      Turkish alphabet, case conversion, normalize, is_valid_word, sort_key   (Faruk)
  words.py         load_guesses / load_answers / encode, word-list build pipeline          (Faruk)
  stats.py         word-list statistics                                                     (Faruk)
scripts/         thin command-line wrappers around the package
tests/           pytest suite
data/            word lists, excluded answers, frequencies, raw sources
results/         machine-readable results (*.json), tables (*.md), charts (*.png)
docs/            weekly reports
```
