# Team roles

*BIL 4112 Artificial Intelligence, Dokuz Eylül University. Team: Berken (lead), Arda, Faruk.*

## Owners per week

| Week | Topic | Owner | Report |
| --- | --- | --- | --- |
| 6 | Problem definition, Turkish alphabet, word lists, statistics, literature | Faruk | [week 6](week6_problem_and_literature.md) |
| 7 | Feedback, game, agent interface, baselines, evaluation, terminal tools | Arda | [week 7](week7_environment_and_baselines.md) |
| 8 | Constraints and proof, CSP solver, pattern table, filter benchmark | Berken | [week 8](week8_constraints_and_pattern_table.md) |
| 9 | Entropy agent and variants | Arda | [week 9](week9_entropy_agent.md) |
| 10 | Expectimax search and exact oracle | Berken | [week 10](week10_expectimax_and_oracle.md) |
| 11 | Experiments, statistics, error analysis | Faruk | [week 11](week11_experiments.md) |
| 12 | Final report, presentation, hand-in | everyone | [final report](final_report.md) |

## Owners per file

| Owner | Package (`wordle_tr/`) | Scripts (`scripts/`) | Tests (`tests/`) |
| --- | --- | --- | --- |
| Faruk | `alphabet.py`, `words.py`, `stats.py`, `analysis.py` | `build_word_lists.py`, `word_stats.py`, `experiments.py`, `plot_style.py` | `test_alphabet.py`, `test_analysis.py` |
| Arda | `feedback.py`, `game.py`, `simulate.py`, `agents/base.py`, `agents/baselines.py`, `agents/entropy.py`, `agents/__init__.py` | `evaluate.py`, `play.py`, `entropy_examples.py` | `test_feedback.py`, `test_game.py`, `test_agents.py`, `test_entropy.py` |
| Berken | `constraints.py`, `csp_solver.py`, `pattern_table.py`, `filters.py`, `oracle.py`, `agents/expectimax.py` | `benchmark_filters.py`, `expectimax_study.py` | `test_week8.py`, `test_expectimax.py` |
| everyone | – | `make_demo.py` | `conftest.py` |

Data (`data/`) belongs to Faruk. The CI workflow (`.github/workflows/tests.yml`)
and the overall integration belong to Berken.

## What each person must be able to explain

Everyone should be able to answer the general questions: what the belief
state is (the candidate set), why the hidden word is uniform, and what the
headline numbers are (expectimax 3.4095, entropy 3.4479, letter frequency
3.7400, random 4.1126).

### Faruk: the problem, the data, and the experiments

* **The problem as a partially observable decision problem**: hidden word,
  guesses, patterns, the candidate set as belief state, and the Bellman
  equation.
* **Turkish pitfalls.**
  - `"İ".lower()` gives two characters and `"i".upper()` gives `"I"`; our
    `to_lower` and `to_upper` fix this.
  - Circumflexes are removed.
  - The subtitle list was lower-cased with the wrong rules (`gİzlİ`).
* **The pipeline**: 140,026 dictionary entries → 5,370 guesses → 1,907 common
  words → 1,900 answers, and why answers must be common words.
* **Statistics.**
  - 42.47 % of answers have a repeated letter.
  - 61.63 % have a one-letter neighbour; the biggest family is SA_MA with 8
    words.
  - ERİKA is the best opener by letter coverage.
* **The literature**: what each paper contributes and the gap (no comparison
  for Turkish).
* **Week 11 statistics.**
  - What a bootstrap 95 % interval means here: variation over similar word
    lists, since the means themselves are exact for our list.
  - How the paired sign-flip test works.
  - Why random → letter frequency → entropy is significant (p = 0.0001) but
    the differences among the search agents are not (p = 0.0621 and 0.6150).
* **Ablations**: non-candidate guesses are worth 0.0711 guesses per word; the
  prior and deeper search change nothing.
* **Error analysis**: difficulty grows with the size of the one-letter family,
  and the DAMAK example (a final 50/50 guess).

### Arda: the game and the information-theoretic agents

* **The two-pass feedback rule with duplicates**: KAPAK → KALEM 🟩🟩⬜⬜⬜ and
  TATLI → OTLAK 🟨🟨⬜🟨⬜. Why the green E in EKLER → KALEM makes the first E
  grey.
* **Base-3 encoding**: 🟩🟩⬜⬜⬜ = 216, all green = 242.
* **Game rules**: invalid guesses do not use a turn; unlimited mode is used in
  experiments.
* **The agent interface**, and why the game loop (not the agent) filters the
  candidates.
* **The baselines**, and why only guessing candidates fails on SA_MA (SAYMA in
  8 guesses; 13 of the 14 failures are one-letter-family words).
* **Entropy H(g) = −Σ p log2 p** and its meaning (expected halvings of the
  candidate set).
  - The worked example: SAÇMA 0.7219 bits vs AVUNÇ 1.9219 bits.
  - The opener KAMER with 5.7713 bits.
* **The variants and their results**:
  - candidates only: 3.5189 and 2 failures;
  - frequency prior: 3.4479, no change;
  - most parts: 3.4184.
* **How the entropy agent solves SAYMA in 3 guesses** (SALYA is not a
  candidate but tests L and Y).

### Berken: constraints, search and optimality

* **The four kinds of constraint** (fixed, forbidden, minimum count, exact
  count) on KAPAK → KALEM.
* **The equivalence proof**.
  - The lemma: green + yellow copies = min(n_g(L), n_w(L)).
  - Why the pattern must be a real one (yellows go to the left-most copies).
* **The CSP model**.
  - Variables, domains (node consistency), counts and the dictionary trie
    (4,932 nodes).
  - Backtracking and forward checking: 614.6 vs 709.5 nodes expanded.
* **The pattern table**.
  - 10,203,000 cells, 10.2 MB, the yellow rule written as counts, the cache.
  - The filter benchmark (118.1× faster than the reference) and why week 9
    needed it (10.0 s vs 38.1 ms per turn).
* **Expectimax**.
  - The tree diagram (min at agent nodes, expectation at chance nodes), the
    recursion, the beam, memoisation and the 2 − 1/s pruning bound.
  - Why it is never worse than entropy (rollout: the entropy choice is in the
    beam, and the leaves are entropy values).
  - The cost table: depth 2 is enough and width hardly matters.
* **The oracle**.
  - The Bellman recursion, branch and bound, and the one-step bound that
    explains most parts.
  - The exact optimum for fixed openers (TARİK 3.4095 = expectimax).
  - NP-hardness, and why we report the bounds 2.9242 ≤ optimum ≤ 3.4095.

## Commands each person runs live

Set up once before the presentation (it builds the 10 MB pattern table cache
on the first run):

```bash
source .venv/bin/activate
python -m pytest                      # about 25 s, all tests pass
```

Commands that write results take `--out-dir /tmp/live`, so the committed
`results/` stay unchanged.

**Faruk**

```bash
python -c "print('İ'.lower(), len('İ'.lower()), 'i'.upper())"     # the Python pitfall
python -c "from wordle_tr.alphabet import to_lower, to_upper; print(to_lower('İSTANBUL'), to_upper('ılık'))"
python scripts/build_word_lists.py --results /tmp/live/word_lists.json   # prints every step: ... 5,370 ... 1,900
python scripts/word_stats.py --out-dir /tmp/live                  # repeated letters, ERİKA, SA_MA
python scripts/experiments.py --out-dir /tmp/live                 # about 1 minute; or open results/comparison.md
```

**Arda**

```bash
python -c "from wordle_tr.feedback import *; print(pattern_to_emoji(feedback('kapak', 'kalem')), feedback('kalem', 'kalem'))"
python scripts/play.py play                                       # someone from the audience plays
python scripts/play.py watch --agent frequency --word sayma       # 8 guesses: SAÇMA, SANMA, SAPMA, ...
python scripts/play.py watch --agent entropy --word sayma         # 3 guesses, with bits per guess
python scripts/entropy_examples.py --out-dir /tmp/live            # openers, worked example (2 s)
```

**Berken**

```bash
python scripts/benchmark_filters.py --states 100 --out-dir /tmp/live   # the four filters agree; speed-ups (5 s)
python -m pytest tests/test_week8.py tests/test_expectimax.py -q        # proof checks, oracle by hand (10 s)
python scripts/play.py watch --agent expectimax --word sayma            # expected guesses at every step
python scripts/play.py assist                                           # suggestions for a game on another site
```

The writing step of `build_word_lists.py` also rewrites `data/guesses.txt`,
`data/answers.txt` and `data/frequencies.tsv` with identical content, so
running it live is safe.

## Suggested presentation (about 20 minutes)

| Part | Speaker | Minutes | Content | Live |
| --- | --- | ---: | --- | --- |
| 1 | Faruk | 3 | Problem, Turkish pitfalls, data, one-letter families | case-conversion one-liners |
| 2 | Arda | 3 | Feedback rule, game, interface, baselines and their failures | `watch --agent frequency --word sayma` |
| 3 | Berken | 4 | Constraints and proof, CSP, pattern table, benchmark | `benchmark_filters.py --states 100` |
| 4 | Arda | 3 | Entropy, worked example, variants | `watch --agent entropy --word sayma` |
| 5 | Berken | 4 | Expectimax, rollout guarantee, oracle, bounds | `watch --agent expectimax`, `assist` |
| 6 | Faruk | 3 | Experiments, significance, error analysis, conclusions | `results/comparison.md` and the charts |
