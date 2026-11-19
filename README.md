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
| 7 | Feedback, game, agent interface, baselines, evaluation | Arda | ✅ done: [doc](docs/week7_environment_and_baselines.md) |
| 8 | Constraints, CSP solver, pattern table, filter benchmark | Berken | ✅ done: [doc](docs/week8_constraints_and_pattern_table.md) |
| 9 | Entropy (information-gain) agent | Arda | ⏳ next |
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
| `python scripts/evaluate.py` | Runs agents on every answer (unlimited guesses; random agents over `--seeds 5`) → `results/baselines.json`, `results/baselines.md`, `results/guess_distribution.png`. Options: `--agent NAME` (repeatable), `--sample N`, `--filter {feedback,constraints,csp,table}`, `--max-guesses N` |
| `python scripts/benchmark_filters.py --full-check --end-to-end` | Times the four filters on 500 random states, checks that they agree and that every pattern-table cell matches `feedback()`, and times a full evaluation with each filter → `results/filters.json`, `results/filters.md` |
| `python scripts/play.py play` | Play in the terminal (coloured tiles, Turkish keyboard; `--no-color` for emoji) |
| `python scripts/play.py watch --agent frequency --word kalem` | Watch an agent solve a word turn by turn |
| `python scripts/play.py assist` | Suggestions while you play on another site: type your word (Enter = suggestion) and its colours (`g`/`y`/`x`) |

Every script has `--help`.

## Results so far

All 1,900 answers, unlimited guesses ([`results/baselines.md`](results/baselines.md)):

| Agent | Mean guesses | % solved ≤ 6 | Max |
| --- | ---: | ---: | ---: |
| random (5 seeds) | 4.1126 ± 0.0352 | 98.38 | 9 |
| letter frequency | 3.7400 | 99.26 | 8 |

Candidate filtering, 500 random states ([`results/filters.md`](results/filters.md)): reference 2.054 ms,
constraints 0.390 ms, CSP 0.502 ms, pattern table 0.017 ms per state, all with identical results.

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
  feedback.py      feedback(), pattern encoding, emoji, parse_pattern, reference filter     (Arda)
  game.py          WordleGame, InvalidGuessError                                            (Arda)
  agents/          Agent interface, registry (make_agent), RandomAgent, LetterFrequencyAgent (Arda)
  simulate.py      play_game, evaluate, summarize                                           (Arda)
  constraints.py   Constraints, ContradictionError, describe()                              (Berken)
  csp_solver.py    WordTrie, CSPSolver (backtracking + forward checking)                    (Berken)
  pattern_table.py compute_pattern_matrix, PatternTable (cached in data/cache/)             (Berken)
  filters.py       the four candidate filters behind one interface                          (Berken)
scripts/         thin command-line wrappers around the package
tests/           pytest suite
data/            word lists, excluded answers, frequencies, raw sources; cache/ (git-ignored)
results/         machine-readable results (*.json), tables (*.md), charts (*.png)
docs/            weekly reports
```
