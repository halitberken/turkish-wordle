# CLAUDE.md — Turkish Wordle Solver (BIL 4112 Artificial Intelligence)

You are building, from an empty repository, a term project for the course BIL 4112 Artificial Intelligence, Dokuz Eylül University. Team: Berken (lead), Arda, Faruk.

**Goal:** AI agents that find a hidden 5-letter **Turkish** word in as few guesses as possible, a fair, reproducible comparison of those agents (constraint-based candidate filtering (CSP), information theory (entropy) and expectimax search), and finally a playable web demo on the internet.

Work **phase by phase** (section 6). Finish a phase, make its tests pass, write its results and its doc, commit, then stop and summarize for me before starting the next phase. Do not jump ahead.

---

## 1. Ground rules

- **Language: English everywhere.** Code, comments, docstrings, CLI sub-commands, flags and messages, result files, chart labels, `README.md` and `docs/*.md`. The only Turkish is the game data itself (the words) and Turkish words used as examples.
- **Python ≥ 3.10.** Runtime dependency: `numpy` only. Dev: `matplotlib`, `pytest`. Nothing else without asking me (the web demo in Phase 8 has its own small toolchain, see there).
- **Package layout:** `wordle_tr/` is an importable package; `scripts/` holds thin CLI wrappers (argparse) around package functions. No logic that tests need lives only in a script.
- **Determinism.** Every random process takes a seed. Rerunning a script with the same arguments must give identical numbers.
- **Never invent numbers.** Every number in a doc or README must come from a file in `results/` that a script produced. If a number in this spec disagrees with what you measure, report the measured number and tell me.
- **Type hints** on public functions, small modules, no premature abstraction. PEP 8.
- **Commit after each milestone** with a clear message. Don't commit `data/cache/`, virtualenvs, `node_modules/` or `__pycache__`.

## 2. Problem definition (goes in `docs/week6_problem_and_literature.md`)

The agent guesses a hidden 5-letter Turkish word in at most 6 tries. After each guess every letter gets a colour: **green** (right letter, right position), **yellow** (in the word, wrong position), **grey** (not in the word, or all its copies already accounted for).

| Concept | Definition |
| --- | --- |
| Hidden word | s ∈ A, A = answer list (~1,900 words), assumed uniform |
| Action | guess g ∈ G, G = guess list (~5,370 words), A ⊆ G |
| Observation | pattern p = f(g, s), one of 3^5 = 243 |
| Belief state | candidate set C_t = {w ∈ A : f(g_i, w) = p_i for all i ≤ t}, C_0 = A |
| Transition | C_{t+1} = {w ∈ C_t : f(g_{t+1}, w) = p_{t+1}} |
| Objective | minimise expected number of guesses; secondary: % solved within 6 |

Frame it as a partially observable decision problem (the candidate set is the belief state) and tie it to course topics: CSP (week 8), probability / information theory (week 9), search with chance nodes / expectimax (week 10).

## 3. Turkish-specific requirements (must be handled correctly)

- **Alphabet:** 29 letters `abcçdefgğhıijklmnoöprsştuüvyz` (no q, w, x). Sorting follows this order, not Unicode order.
- **Case conversion:** Python's `"İ".lower()` returns 2 characters and `"i".upper()` returns `"I"`. Write `to_lower` / `to_upper` that map I↔ı and İ↔i correctly. Store words lowercase internally. (The same pitfall exists in JavaScript: use `toLocaleUpperCase("tr")` / `toLocaleLowerCase("tr")` in Phase 8.)
- **Circumflex:** normalise â→a, î→i, û→u (kâğıt → kağıt, hâlâ → hala).
- **Duplicate letters** are common (~40 % of answers): the feedback function must implement the standard two-pass rule exactly.

## 4. Data

### Raw sources

| File | Source | Use |
| --- | --- | --- |
| `data/raw/tdk_cannuhlar.txt` | github.com/CanNuhlar/Turkce-Kelime-Listesi (from the TDK dictionary) | valid words |
| `data/raw/tdk_mertemin.txt` | github.com/mertemin/turkish-word-list (from TDK) | valid words |
| `data/raw/opensubtitles_tr_50k.txt` | github.com/hermitdave/FrequencyWords, `content/2018/tr/tr_50k.txt` | how common a word is |

**Two ways to get them; I'll tell you which one at the start of Phase 1:**

- **Option A, copy:** I put an existing `data/raw/` folder into the repo. Use it as is. This is the fastest route and should reproduce the earlier word-list counts exactly.
- **Option B, download:** write `scripts/fetch_raw_data.py` that downloads the three files from the URLs above (pin the raw GitHub URLs, print size and SHA-256 of each, refuse to overwrite existing files unless `--force`). Then commit the downloaded files so the build never depends on the network again. Upstream lists can change, so counts may differ slightly from the reference values; report the differences.

If I don't say, ask me before downloading.

### Pipeline: `scripts/build_word_lists.py`

1. Read both dictionary lists (≈140,000 entries total).
2. Drop proper nouns (entries starting with an upper-case letter), multi-word or punctuated entries, and anything that is not exactly 5 letters after normalisation. Normalise circumflexes.
3. Deduplicate → **guess list** `data/guesses.txt` (expected ≈5,370).
4. Words that also appear in the 50k subtitle frequency list are "common" (≈1,907).
5. Remove a small hand-curated set of offensive words (profanity, sexual content, slurs) listed in `data/excluded_answers.txt`, one word per line with a `#` comment header. Write the list yourself, keep it short, and show it to me.
6. Result → **answer list** `data/answers.txt` (expected ≈1,900). Also write `data/frequencies.tsv` (`word<TAB>subtitle_count`) for later weighting.

Print the count after each step; these counts go into the week 6 doc. Output files are sorted in Turkish alphabetical order with a one-line `#` header. A test asserts that every word in both lists is 5 valid Turkish letters, lowercase, unique, and that answers ⊆ guesses.

## 5. Target repository layout

```
wordle_tr/
  __init__.py
  alphabet.py        Turkish alphabet, case conversion, normalize, is_valid_word, sort_key
  words.py           load_guesses(), load_answers(), encode(words) -> np.ndarray (letter codes 0..28)
  feedback.py        feedback(), pattern encoding/decoding, emoji, parse_pattern, filter_candidates
  game.py            WordleGame, InvalidGuessError
  agents/
    __init__.py      AGENTS registry + make_agent(name, seed)
    base.py          abstract Agent
    baselines.py     RandomAgent, LetterFrequencyAgent
    entropy.py       (phase 4)
    expectimax.py    (phase 5)
  simulate.py        play_game(), evaluate(), summarize(), GameResult, Summary
  constraints.py     Constraints, ContradictionError
  csp_solver.py      WordTrie, CSPSolver (backtracking + forward checking)
  pattern_table.py   compute_pattern_matrix(), PatternTable (cached .npy)
  filters.py         all filtering methods behind one interface
  oracle.py          (phase 5) exact / bounded-depth optimal solver
scripts/
  fetch_raw_data.py (option B)  build_word_lists.py  word_stats.py  play.py  evaluate.py
  benchmark_filters.py  experiments.py  export_web_data.py
tests/
  conftest.py  test_alphabet.py  test_feedback.py  test_game.py  test_agents.py
  test_week8.py  test_entropy.py  test_expectimax.py  test_web_export.py
data/   guesses.txt  answers.txt  excluded_answers.txt  frequencies.tsv  raw/  cache/ (git-ignored)
results/  *.json (machine-readable)  *.md (tables)  *.png (charts)
docs/   week6_….md  week7_….md  week8_….md  week9_….md  week10_….md  week11_….md
        final_report.md  team_roles.md  demo/ (screenshots)
web/    (phase 8) static playable demo
.github/workflows/  tests.yml  deploy-web.yml
README.md  pyproject.toml  requirements.txt  .gitignore
```

## 6. Phases

### Phase 1 — Week 6: alphabet, word lists, statistics (owner: Faruk)

Build:
- `alphabet.py`, `words.py`, the data step (section 4, option A or B), `scripts/build_word_lists.py`.
- `scripts/word_stats.py`: for each letter, the % of answers containing it; % of answers with a repeated letter; best openers by distinct-letter coverage. Save `results/word_stats.json` and a bar chart `results/letter_frequency.png`.
- `docs/week6_problem_and_literature.md`: problem definition (section 2), Turkish challenges (section 3, with real numbers from `word_stats.json`, and the observation that many answers form one-letter-apart families such as SAÇMA/SANMA/SAPMA/SAVMA/SAYMA), data pipeline with counts, and a literature table:
  - G. Sanderson (3Blue1Brown), *Solving Wordle using information theory*, 2022 → entropy agent
  - A. Selby, *The best strategies for Wordle*, 2022 → exact optimum reference (SALET, 3.4212 avg)
  - D. Bertsimas, A. Paskov, *An Exact Solution to Wordle*, Operations Research, 2025 → oracle via Bellman / DP
  - D. Lokshtanov, B. Subercaseaux, *Wordle Is NP-Hard*, FUN 2022 → why bounded-depth search
  - S. Bhambri, A. Bhattacharjee, D. Bertsekas, *Reinforcement Learning Methods for Wordle: A POMDP/Adaptive Control Approach*, 2022 → rollout / lookahead helps
  - R. I. Greenberg, *Effective Wordle Heuristics*, 2024 → "most partitions" heuristic
  - Russell & Norvig, *AIMA* 4th ed., ch. 5 (expectiminimax) and ch. 6 (CSP)
  - Stated gap: no systematic comparison of methods on **Turkish** Wordle found; that is the contribution.
  Verify each citation's link before writing it; if you cannot verify one, mark it for me instead of guessing.

Tests (`test_alphabet.py`): 29 letters; `to_lower("İSTANBUL") == "istanbul"`, `to_upper("ılık") == "ILIK"`; normalize removes circumflexes and surrounding whitespace; `is_valid_word`; `sort_key` puts ç after c and ı before i; word lists are clean (section 4).

### Phase 2 — Week 7: feedback, game, agent interface, baselines, evaluation (owner: Arda)

Build:
- `feedback(guess, answer) -> int`, two passes: (1) mark greens, count the answer's unmatched letters; (2) left to right, a non-green letter is yellow if an unused copy remains (consume it), else grey.
- **Pattern encoding:** base 3, grey 0, yellow 1, green 2, position 0 is the most significant digit (pick one convention and document it). 0..242, **242 = all green** (`ALL_GREEN`). Helpers: `encode_colors`, `decode_pattern`, `pattern_to_emoji` (⬜🟨🟩), `parse_pattern("ggy..")` with letters **g = green, y = yellow, x = grey** (also accept emoji), `is_consistent(word, history)`, `filter_candidates(candidates, guess, pattern)` (reference filter: recompute feedback).
- `WordleGame(answer, allowed_guesses=None, max_guesses=6)`: `play(guess) -> pattern`, `history`, `guesses_used`, `won`, `over`. An invalid guess (wrong length, not in list, game over) raises `InvalidGuessError` and **does not consume a turn**. `max_guesses=None` means unlimited (used in experiments so we see the full distribution beyond 6).
- **Agent interface:** `Agent.choose_guess(history, candidates) -> str`, plus `reset()`. `History = list[tuple[str, int]]`. The **game loop owns candidate filtering**, not the agent; this lets us swap the filter without touching agents.
- Baselines: `RandomAgent(seed)` picks a uniformly random candidate. `LetterFrequencyAgent`: score each candidate by summing, over its *distinct* letters, how many candidates contain that letter; pick the max (ties broken deterministically, e.g. Turkish alphabetical order). Its first guess should be a high-coverage word (the previous build got ERİKA; report what you get). Registry names: `random`, `frequency`.
- `simulate.play_game(agent, answer, answers, allowed, filter_fn, max_guesses=None) -> GameResult` (guesses, patterns, candidate counts after each guess, time per guess). `evaluate()` runs an agent on every answer; `summarize()` gives mean, % solved ≤ 6, max, guess-count histogram, time per guess, and the 10 hardest words.
- `scripts/evaluate.py`: `--agent` (repeatable), `--sample N` (random subset), `--filter {feedback,constraints,table}`, `--seeds` (random agent repeated over 5 seeds, report mean ± std). Writes `results/baselines.json`, `results/baselines.md`, `results/guess_distribution.png`.
- `scripts/play.py` with three modes:
  - `play`: human plays in the terminal with ANSI coloured tiles (`--no-color` falls back to emoji).
  - `watch --agent frequency --word kalem`: watch an agent solve a word, showing guess, pattern and remaining candidates each turn.
  - `assist`: helper while playing on another site; agent suggests, user types the word they actually tried (Enter = suggestion) and the pattern; show remaining count and plain-English known facts (`Constraints.describe()`); detect contradictory input.
- `docs/week7_environment_and_baselines.md`: feedback rule with duplicate-letter examples, encoding, game, interface, baselines, results table + histogram, **error analysis** of the words the frequency agent fails within 6 (expect one-letter-apart families like SA_MA), and why guessing only from candidates causes that (motivates week 9).

Tests:
- `test_feedback.py` must include these duplicate-letter cases (guess, answer → pattern):
  KAPAK/KALEM → 🟩🟩⬜⬜⬜; EKLER/KALEM → ⬜🟨🟩🟩⬜; TATLI/OTLAK → 🟨🟨⬜🟨⬜; KEKİK/KAYAK → 🟩⬜⬜⬜🟩; plus all-green and all-grey. Encoding round-trip for all 243 patterns; `parse_pattern`; filtered candidates always contain the true answer (300 random histories, seed 1234).
- `test_game.py`: win in two; game ends after 6; invalid guesses rejected without using a turn; unlimited mode.
- `test_agents.py`: both agents solve a sample of answers (unlimited mode); frequency agent deterministic; random agent reproducible by seed; `summarize` fields correct.

**Reference values from the previous build** (all 1,900 answers, unlimited guesses): random ≈ 4.11 ± 0.01 avg, ≈ 98.3 % within 6; letter-frequency ≈ 3.74 avg, ≈ 99.3 % within 6, worst 8. If your lists match, you should land very close; if not, explain the difference.

### Phase 3 — Week 8: constraints, CSP solver, pattern table, filter benchmark (owner: Berken)

Build:
- **`Constraints`** from (guess, pattern) observations, four kinds:
  | Kind | Rule |
  | --- | --- |
  | Fixed letter | green → that letter at that position |
  | Forbidden letter | yellow/grey → that letter not at that position |
  | Minimum count | k = green + yellow copies of L in the guess → L appears ≥ k times |
  | Exact count | if any copy of L is grey → L appears exactly k times (k = 0: absent) |
  Combining observations: take the max of minimums and the min of maximums. Inconsistent input raises `ContradictionError(ValueError)`. Methods: `from_history`, `add_observation`, `is_satisfied(word)`, `domains()` (per-position allowed letters = node consistency), `describe()` → English sentences, e.g. `Letter 1 is K; letter 2 is A; not in word: P; A is not elsewhere`.
- **Equivalence proof** (in the doc): for a real pattern p = f(g, s), a word w satisfies the constraints of (g, p) ⇔ f(g, w) = p. Key lemma: in any feedback(g, w), green + yellow copies of L = min(n_g(L), n_w(L)). Prove both directions; note yellows are assigned to the left-most non-green copies, so equal counts imply equal positions.
- **`CSPSolver`**: variables X1..X5, domains from `Constraints.domains()`, global letter-count constraints, and the dictionary constraint enforced by searching inside a **trie** of the answer list. Left-to-right **backtracking**; after each assignment **forward checking**: prune if a letter's max count is exceeded, or if the letters still required can't fit in the remaining positions' domains. Return the solutions plus search stats (nodes expanded) and report average nodes expanded vs. trie size.
- **`PatternTable`**: precompute M[g, a] = feedback(g, a) for all guesses × answers as `uint8` (≈10.2 M cells, ≈10 MB). Compute it **vectorised in numpy** (no Python loop over pairs). Yellow rule as counts: a non-green position i with letter L is yellow iff (number of L in the answer's non-green positions) > (number of non-green L in the guess before i); build these from 5×5 letter-equality matrices. Cache to `data/cache/pattern_table_<hash of lists>.npy`; rebuild if the word lists change. API: `pattern(g, a)`, `all_ids()`, `filter_ids(ids, g, p)` (one line: `ids[M[g, ids] == p]`), `filter_words`, `partition_counts(g, ids) = np.bincount(M[g, ids], minlength=243)`.
- **`filters.py`**: one interface over four methods: recompute-feedback (reference), constraint check, CSP, pattern table.
- **`scripts/benchmark_filters.py`**: `--states 500` random game states (seeded); time each method (`--repeat`); assert all four give identical candidate sets; `--full-check` checks **every** table cell against scalar `feedback()` (must be 0 mismatches); `--end-to-end` times the full letter-frequency evaluation with each filter and confirms identical results. Writes `results/filters.json`, `results/filters.md`.
- `docs/week8_constraints_and_pattern_table.md`: why it matters (week 9 needs 5,370 × 1,900 ≈ 10 M feedback evaluations per turn: measure the scalar cost and the table cost and state both), constraints table with the KAPAK→KALEM example, proof, CSP model table, trie / backtracking / forward checking, pattern table and its yellow rule, benchmark table, bridge to week 9.

Tests (`test_week8.py`): constraints match the reference filter on 300 random histories and on a sample of ≥ 15,000 random (guess, answer) pairs; CSP matches the reference; pattern table matches scalar feedback on a sample and on hand-made tricky duplicate cases; table filter matches reference; incremental filtering agrees across methods; `partition_counts` sums to the candidate count; `describe()` text; contradictory feedback detected.

Reference values from the previous build (machine-dependent, for orientation only): reference ≈ 8 ms per filter, constraints ≈ 4.5× faster, CSP ≈ 6.7× faster, table ≈ 300× faster; table build ≈ 4 s, load from cache ≈ 0.01 s.

### Phase 4 — Week 9: entropy (information-gain) agent (owner: Arda)

Build `agents/entropy.py`:
- For each candidate guess g (search over the **full guess list**, not only candidates), get the partition of current candidates via `partition_counts`, compute expected information H(g) = −Σ p_k log2 p_k. Pick max H; tie-break in favour of a word that is itself a candidate, then alphabetically.
- If ≤ 2 candidates remain, guess a candidate. Precompute and cache the first guess (it is the same every game).
- Variants (constructor options, each a registered agent name): `entropy` (uniform prior), `entropy_candidates` (guesses restricted to candidates, to isolate the effect of non-candidate guesses), `entropy_freq` (prior weighted by subtitle frequency from `frequencies.tsv`, e.g. a sigmoid over log-rank), and `most_parts` (Greenberg: maximise number of non-empty partitions).
- Keep the agent interface unchanged; the agent receives a `PatternTable` at construction.
- Doc `docs/week9_entropy_agent.md`: formula, a worked example on a small candidate set, best openers by entropy (top 10 with bits), results vs. baselines, and how the SAYMA family is now handled (show the actual game).

Tests: entropy of a known partition; agent always returns a word from the guess list; solves every answer in unlimited mode; deterministic; first guess cached; `entropy` mean ≤ letter-frequency mean on the full list.

Acceptance: full evaluation of `entropy` on all answers in well under a minute; expected to beat 3.74 clearly and drive failures (> 6) toward zero. Report what you measure.

### Phase 5 — Week 10: expectimax search and oracle (owner: Berken)

Build `agents/expectimax.py`:
- Agent node = choose a guess; chance node = pattern, probability = |partition| / |C|. Value = expected remaining guesses. Leaf / cut-off at depth d uses a heuristic estimate (e.g. a fitted function of candidate count, or the entropy agent's value); document the choice.
- To keep it tractable, at each agent node consider only the top-k guesses by entropy (beam), e.g. k ∈ {10, 25, 50}; memoise on the sorted tuple of candidate ids. Depth and k are CLI parameters (`--depth`, `--width`).
- `oracle.py`: exact minimum expected guesses (Bellman recursion) for small candidate sets, used (a) to verify expectimax on small sub-problems and (b) as the optimum reference. If the full answer list is out of reach in reasonable time, compute the exact optimum for a fixed opener only, or bound it, and say so honestly in the doc (cite the NP-hardness result).
- Hard mode (optional, flag `--hard`): every guess must satisfy all previous constraints (use `Constraints.is_satisfied`).
- Doc `docs/week10_expectimax_and_oracle.md`: tree diagram, recursion, pruning/beam/memoisation, cost table (depth × k vs. time and mean guesses), comparison with the oracle where available.

Tests: on tiny hand-made word sets the oracle value is verified by hand; expectimax with full width and enough depth equals the oracle on small sets; expectimax never does worse than entropy on a fixed sample (or document where it does).

### Phase 6 — Week 11: experiments and analysis (owner: Faruk)

`scripts/experiments.py` runs every agent on all answers with unlimited guesses, then writes `results/comparison.json|md` and charts:
- Table: agent, mean ± 95 % CI (bootstrap, seeded), % within 6, max guesses, failures, time per guess, total time.
- Guess-count histogram for all agents; cumulative "solved by turn t" curve.
- Paired comparison between consecutive agents (same secret words): mean difference with bootstrap CI, or a Wilcoxon signed-rank test if scipy is approved (ask first).
- Ablations: entropy over candidates only vs. full guess list; uniform vs. frequency prior; expectimax depth/width.
- Hard mode vs. normal mode if implemented.
- Error analysis: hardest words per agent and why (letter families), with one illustrated game.
- Doc `docs/week11_experiments.md`.

### Phase 7 — Week 12: final report, presentation, hand-in (everyone)

- Update `README.md`: one-paragraph summary, status table by week, setup, usage for every script, headline results table (from `results/`), folder map with owners, data sources, demo screenshots in `docs/demo/` (terminal output of `watch`, `play`, `assist`, and the test run).
- `docs/final_report.md`: introduction, problem, data, methods (CSP, entropy, expectimax, oracle), experiments, discussion, limitations, conclusion, references. Every number traceable to `results/`.
- `docs/team_roles.md`: owner per week and file, what each person must be able to explain in the presentation, and the commands each person runs live.
- A clean-clone check: fresh venv, `pip install -r requirements.txt`, `python -m pytest` passes, every script in the README runs.
- Add `.github/workflows/tests.yml` that runs `pytest` on every push.

### Phase 8 — Playable web demo on the internet (after the project is complete)

**Goal:** anyone with the link can play Turkish Wordle in the browser and watch or ask the AI agents for help, with no server and no install. Host it as a **static site on GitHub Pages**, deployed automatically from `main`.

**Approach:** a static front end in plain **TypeScript + Vite** (no UI framework needed; ask me before adding one). The Python package stays the source of truth; the browser gets a faithful port of only what it needs (alphabet, feedback, filtering, entropy agent, frequency agent). Do **not** ship the 10 MB pattern table; compute feedback in the browser (2,000 × 5,370 per entropy step is fine inside a **Web Worker**), and precompute the expensive first guess in Python.

Build:
- `scripts/export_web_data.py` writes `web/public/data/`:
  - `guesses.json`, `answers.json` (lowercase, Turkish order),
  - `openers.json`: the best first guess per agent, and the best second guess for each first-turn pattern of the entropy agent (so turn 2 is instant),
  - `feedback_fixtures.json`: ~2,000 random (guess, answer, pattern) triples plus all the duplicate-letter cases from Phase 2, used to test the TypeScript port against Python,
  - `summary.json`: headline results from `results/comparison.json` for the "How it works" page.
- `web/` app with three modes (tabs), matching `scripts/play.py`:
  1. **Play:** 6×5 grid, on-screen **Turkish keyboard** (all 29 letters, including Ç Ğ I İ Ö Ş Ü; physical keyboard input works too, with correct İ/ı handling), tile flip animation, keyboard keys coloured by best known state, "not in word list" shake, win/lose message, share result as an emoji grid (copy to clipboard), new random game, and a **daily word** mode (deterministic from the date, same for everyone).
  2. **Watch the AI:** pick an agent (frequency, entropy) and a word (or random), step through or auto-play; show each guess, its pattern, remaining candidate count and, for entropy, the expected bits of the chosen guess.
  3. **Assist:** user types the guess they made elsewhere and clicks tiles to set colours; the agent suggests the next guess and shows the remaining candidates (first 20) and plain-English known facts; detects contradictory input.
  - A short **How it works** page: problem, the three methods, the results table and a link to the GitHub repo and final report.
- Design: original look (own colour palette and name, e.g. "Kelime Avı" or similar; do not copy the NYT Wordle branding or layout assets), accessible colours (also a high-contrast/colour-blind toggle using shapes or alternative colours), dark and light themes, works at phone width (≥ 360 px) and on desktop, no horizontal scroll.
- Persistence: statistics (played, win %, streak, guess distribution) and settings in `localStorage`, wrapped in try/catch so the page still works when storage is blocked.
- Performance: first load under ~1 MB gzipped; entropy suggestion under ~1 s on a mid-range phone (Web Worker, typed arrays, encode words as letter codes once).

Tests and CI:
- `web/` unit tests with **Vitest**: the TypeScript `feedback` matches every triple in `feedback_fixtures.json`; Turkish case conversion; filtering keeps the answer; the TS entropy agent picks the same first and second guesses as `openers.json`.
- One **Playwright** smoke test: load the page, play a full game by typing, check that the grid colours and the win message appear, and that the Turkish keyboard works.
- `tests/test_web_export.py` (Python): exported files exist, are valid JSON, and match the word lists.
- `.github/workflows/deploy-web.yml`: on push to `main`, run Python export, `npm ci`, Vitest, build, and deploy `web/dist` to GitHub Pages (set Vite `base` to the repo name). Tell me which repository settings I need to change (Settings → Pages → Source: GitHub Actions).

Acceptance:
- The public URL works on a phone and a laptop; all three modes work; a full game on a fixed word gives the same patterns as `python scripts/play.py watch --agent entropy --word <word>`.
- The URL, a screenshot and a "Try it online" line are added to `README.md` and `docs/final_report.md`.

## 7. Conventions for tests and runtime

- Shared fixtures in `tests/conftest.py`: `guesses`, `answers` (session scope), `random_histories` (300 states, seed 1234, 1–4 random guesses each), `table` (session-scoped `PatternTable`), `solver`.
- The whole Python suite must run in under ~1 minute on a laptop; mark anything slower with `@pytest.mark.slow` and skip it by default.
- Every script has a helpful `--help`, prints a short summary, and writes its outputs to `results/` (or `web/public/data/` for the export).

## 8. Definition of done (per phase)

1. `python -m pytest` is green (and `npm test` in `web/` for Phase 8).
2. The phase's script runs from a clean clone and regenerates its output files.
3. The phase's doc exists, and every number in it matches `results/`.
4. README status table updated.
5. Committed, and you've sent me a short summary: what was built, the key numbers, anything that differs from this spec and why.
