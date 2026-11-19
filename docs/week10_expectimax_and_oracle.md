# Week 10: Expectimax search and the exact oracle

*Owner: Berken. BIL 4112 Artificial Intelligence, Dokuz Eylül University.*

The entropy agent of week 9 is greedy. It maximises the information of the
next guess, which is only a proxy for what we want: few guesses. This week
searches for the guess that minimises the **expected number of guesses**
directly, by looking ahead over guesses and patterns. The exact optimum
(Bellman recursion) serves as the reference.

Every number below comes from `results/expectimax.md` / `results/expectimax.json`,
written by:

```bash
python scripts/expectimax_study.py      # depths 1-3 x widths 10/25/50, oracle comparisons
```

## 1. Wordle as a game against chance

There is no opponent: after the agent's move, "nature" chooses the hidden word.
For the agent, this is a chance node whose outcome is the pattern. With the
uniform prior, pattern p has probability |C_p| / |C|, where C_p are the
candidates that would produce it. This is expectiminimax (AIMA §5.5,
stochastic games) without a MAX player: agent nodes **minimise**, chance nodes
take the **expectation**.

```text
                 C                         agent node: choose a guess (minimum over the beam)
        ┌────────┼────────┐
        g1       g2  …    gk               beam: the k best guesses by entropy
        │
        ▼                                  chance node: pattern p with probability |C_p| / |C|
 ┌──────┼──────┬─────────┐
C_p1   C_p2    …     🟩🟩🟩🟩🟩              agent nodes one level down; all green = solved (0 more guesses)
 ⋮
depth 0: the entropy agent's value is used (see section 2)
```

## 2. The recursion

The value of a node is the expected number of guesses still needed, the
current one included. For a set of candidates C and a guess g:

  Q_d(C, g) = 1 + Σ_{p ≠ all green} (|C_p| / |C|) · V_{d−1}(C_p)

  V_d(C) = 1 if |C| = 1;  1.5 if |C| = 2;  min over the beam of Q_d(C, g) otherwise

With two candidates, guessing one of them gives 1 or 2 guesses, 1.5 on average,
and nothing does better. The agent (`wordle_tr/agents/expectimax.py`) plays
the guess that attains V_d at the current position, and it searches again
after every pattern.

**Leaf value (the cut-off at depth 0).** V_0(C) is the **exact expected number
of guesses of the entropy agent** from C. It is computed by following the
entropy agent's choice through every pattern, and memoised. We chose this over
a fitted function of the candidate count for three reasons:

1. **It is an achievable value**, so every V_d is the value of a real plan.
2. **It gives a guarantee.** The entropy agent's own choice is always first in
   the beam, so the search is a *rollout* of the entropy policy
   (Bhambri, Bhattacharjee & Bertsekas, 2022). For every candidate set C:
   **V^π(C) ≤ V_d(C) ≤ V_{d−1}(C) ≤ … ≤ V_0(C) = V_entropy(C)**, where π is
   the expectimax agent that searches again every turn.

   *Proof sketch.*
   - V_d ≤ V_{d−1}: by induction on d. V_d(C) ≤ Q_d(C, g_entropy) =
     1 + Σ p·V_{d−1}(C_p) ≤ 1 + Σ p·V_{d−2}(C_p) = Q_{d−1}(C, g_entropy) …,
     down to V_0 = V_entropy.
   - V^π ≤ V_d: by induction on |C|. π plays the minimising guess g*, so
     V^π(C) = 1 + Σ p·V^π(C_p) ≤ 1 + Σ p·V_d(C_p) ≤ 1 + Σ p·V_{d−1}(C_p) =
     V_d(C).
   - Guesses that give no information are never tried, so every C_p is smaller
     than C.

   The tests check both inequalities on 25 random positions.
3. **It needs no extra data or parameters.**

## 3. Making the search tractable

* **Beam.** At each agent node only the `width` = k best guesses by entropy are
  tried (k = 10, 25 or 50), instead of 5,370.
* **Memoisation.** Values are stored per (sorted candidate ids, depth) and
  reused across turns and across games: a position reached in many games is
  searched once. The same holds for the entropy values at the leaves.
* **Pruning (branch and bound).** Before a part of size s is searched, it is
  counted at its lower bound 2 − 1/s (see section 5). A guess is abandoned as
  soon as this optimistic total reaches the best value found so far. Every V_d
  is the value of a real plan, so it is at least the optimum, which is at least
  2 − 1/s; the bound is therefore safe.
* Sets of 1 or 2 candidates are solved directly (1 and 1.5).

Depth and width are command-line options (`--depth`, `--width`) of
`evaluate.py` and `play.py`. The registered agent `expectimax` uses depth 2
and width 10, the cheapest setting that reaches the best mean in the table
below.

## 4. Cost table

All 1,900 answers, unlimited guesses. "First move" is the search for the
opening guess. "Total" includes the first move and all 1,900 games.

| Depth | Width | Mean guesses | Max | Opener | Value predicted at the opening | First move s | Total s | Nodes |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 10 | 3.4100 | 5 | TARİK | 3.4184 | 2.0 | 2.8 | 244 |
| 1 | 25 | 3.4100 | 5 | TARİK | 3.4184 | 4.5 | 5.5 | 244 |
| 1 | 50 | 3.4100 | 5 | TARİK | 3.4184 | 7.3 | 8.6 | 244 |
| 2 | 10 | **3.4095** | 5 | TARİK | 3.4100 | 4.4 | 5.1 | 1069 |
| 2 | 25 | 3.4095 | 5 | TARİK | 3.4100 | 14.5 | 15.3 | 1709 |
| 2 | 50 | 3.4095 | 5 | TARİK | 3.4100 | 36.6 | 37.9 | 2477 |
| 3 | 10 | 3.4095 | 5 | TARİK | 3.4095 | 5.2 | 5.8 | 4612 |
| 3 | 25 | 3.4095 | 5 | TARİK | 3.4095 | 20.1 | 20.9 | 12787 |
| 3 | 50 | 3.4095 | 5 | TARİK | 3.4095 | 61.5 | 62.9 | 28624 |

For comparison: entropy 3.4479 (opener KAMER) and most parts 3.4184 (opener KERİM).

* **Every configuration beats both.** All choose the opener **TARİK**, which
  ranks second by entropy (week 9).
* **Depth matters a little, width hardly at all.** One step of lookahead gives
  3.4100; two steps give 3.4095, and a third step changes nothing. A beam of 10
  already contains the right guesses; wider beams only cost time.
* **The plan is pessimistic.** The value predicted at the opening is the value
  of the plan "look ahead d steps, then play entropy". Because the agent searches
  again every turn, it does at least as well: depth 1 predicts 3.4184 and
  achieves 3.4100.
* **It optimises the average, not every word.** Compared with entropy, depth 2
  needs fewer guesses for 466 words and more for 396. The mean, which is what
  the search minimises, is lower.
* Memoisation keeps everything cheap: the depth-2, width-10 agent plays all
  1,900 games in 5.1 s.

## 5. The exact oracle

`wordle_tr/oracle.py` computes the exact optimum

  V*(C) = 1 if |C| = 1,   V*(C) = min_g [ 1 + Σ_{p ≠ all green} (|C_p| / |C|) · V*(C_p) ]

over **all 5,370 guesses**, by depth-first branch and bound:

* **Merging.** Guesses that split C in the same way are merged.
* **Ordering.** The options are tried in order of a lower bound, so good
  solutions come first.
* **Stopping.** A branch stops as soon as its bound reaches the best value
  found.
* **Memoisation.** Exact values and proven lower bounds are stored per
  candidate set.

Two lower bounds make this fast enough:

* **2 − 1/s for s candidates.** At best, the first guess is a candidate that
  gives every other candidate its own pattern. That costs 1 + (s − 1)/s · 1.
* **One step deeper.** A guess g that splits n candidates into m(g) parts (a
  win counts as a part) leaves parts of size s that each need at least 2 − 1/s.
  These add up to **V*(C) ≥ 1 + (2n − m(g) − [g is a candidate]) / n** for the
  best g. This bound is lowest for the guess with the **most parts**, ties
  going to candidates. It explains why Greenberg's most-parts rule works so
  well (week 9): it greedily minimises this bound.

**Hand-checked examples** (in `tests/test_expectimax.py`):

* **KALEM, KALIN, KAYAK** → 5/3. KALEM gives three different patterns, so
  1 + 2/3 · 1.
* **The family SAÇMA, SANMA, SAPMA, SAVMA, if only these 4 words may be
  guessed** → 2.5. Each guess tests a single word, so they take 1, 2, 3 and 4
  guesses.
* **The same family with AVUNÇ allowed** → 2.0. AVUNÇ gives four different
  patterns, so 1 + 1.

The tests also check that expectimax with every guess in the beam
(`width=None`) and enough depth returns exactly V* on 15 real candidate sets.

**Small candidate sets.** We took 200 candidate sets (3–30 words, mean 11.2)
from seeded random game states and compared each policy with the optimum
(exact means of the policies, following their choices through every pattern):

| Policy | Mean guesses | Mean gap to optimum | Largest gap | Sets solved optimally |
| --- | ---: | ---: | ---: | ---: |
| optimum (oracle) | 2.0094 | – | – | 200 / 200 |
| entropy | 2.0126 | 0.0032 | 0.0714 | 187 / 200 |
| most parts | 2.0118 | 0.0024 | 0.0714 | 191 / 200 |
| expectimax, depth 1, width 10 | 2.0094 | 0.0000 | 0.0000 | 200 / 200 |
| expectimax, depth 2, width 10 | 2.0094 | 0.0000 | 0.0000 | 200 / 200 |
| expectimax, depth 3, width 10 | 2.0094 | 0.0000 | 0.0000 | 200 / 200 |

**Fixed openers.** The full answer list is within reach once the opener is
fixed. V*(answers | opener) = 1 + the size-weighted exact optimum of every part
the opener leaves. Each opener took between 2.6 and 22.3 s. We solved 16
promising openers: the openers of our agents, the top 10 by entropy and the top
10 by number of parts.

| Opener | Exact optimum | Entropy agent after it | Expectimax (depth 2, width 10) after it |
| --- | ---: | ---: | ---: |
| **TARİK** | **3.4095** | 3.4184 | **3.4095** |
| KERİM | 3.4121 | 3.4305 | 3.4142 |
| SERİN | 3.4211 | 3.4295 | 3.4211 |
| KAMİL | 3.4216 | 3.4305 | 3.4221 |
| SERİM | 3.4226 | 3.4374 | 3.4226 |
| MELİK | 3.4242 | 3.4347 | 3.4247 |
| MALİK | 3.4247 | 3.4379 | 3.4258 |
| KARNİ | 3.4295 | 3.4395 | 3.4300 |
| MERAK | 3.4305 | 3.4421 | 3.4321 |
| SENİR | 3.4321 | 3.4468 | 3.4321 |
| SERAK | 3.4337 | 3.4484 | 3.4342 |
| KENAR | 3.4342 | 3.4453 | 3.4342 |
| KAMER | 3.4358 | 3.4479 | 3.4363 |
| KELAM | 3.4363 | 3.4489 | 3.4384 |
| KALEM | 3.4400 | 3.4484 | 3.4411 |
| KESİN | 3.4426 | 3.4553 | 3.4458 |

* **With TARİK the expectimax agent is optimal**: its 3.4095 is the exact optimum
  for that opener. After four of the other openers (SERİN, SERİM, SENİR, KENAR)
  it is optimal too, and after the rest it stays close. The entropy agent is
  further from the optimum after every opener.
* **The opener matters more than the play after it.** Entropy's own opener
  KAMER cannot do better than 3.4358 even with perfect play afterwards, which
  is worse than entropy after TARİK (3.4184).

**The optimum over all openers.** This would need every opener solved or
bounded: 5,370 searches like the ones above. Deciding whether Wordle can be
won within k guesses is NP-hard (Lokshtanov & Subercaseaux, 2022). The exact
English solutions needed heavy dedicated computation; Selby reports about two
days on a 6-core machine to prove the SALET result. We therefore report a
bound, not a proof:

**2.9242 ≤ optimum ≤ 3.4095.**

* The lower bound is the one-step bound above, minimised over all openers (it
  is lowest for KERİM).
* The upper bound is the exact value with TARİK, the best opener we solved.

For comparison, the optimum for English Wordle is 3.4212 (SALET, Selby 2022),
with a different word list and alphabet.

## 6. Hard mode

Hard mode (every guess must satisfy all previous constraints) is optional in
the project specification and is not implemented.

## 7. Tests

`tests/test_expectimax.py` covers:

* the hand-checked oracle values above;
* the lower bounds on 30 real candidate sets;
* full-width expectimax equal to the oracle on 15 real sets;
* expectimax never worse than entropy in expectation, and never worse than its
  own plan, on 25 random positions (depth 1 and depth 2);
* `policy_value` equal to playing every word;
* the cached opening.

## 8. Bridge to week 11

Week 11 runs every agent on all answers with confidence intervals and paired
comparisons. The expected ranking is visible already: expectimax (3.4095) <
most parts (3.4184) < entropy (3.4479) < letter frequency (3.7400) < random.
Week 11 checks whether these differences are significant.
