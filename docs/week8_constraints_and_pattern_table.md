# Week 8: Constraints, CSP solver and pattern table

*Owner: Berken. BIL 4112 Artificial Intelligence, Dokuz Eylül University.*

This week looks at candidate filtering in three new ways:

* as **constraints** derived from the feedback (with a proof that they are exactly
  equivalent to it);
* as a **constraint satisfaction problem** solved by backtracking with forward
  checking in a trie;
* as a lookup in a precomputed **pattern table**.

All four filters, including the week 7 reference, sit behind one interface
and return identical results. Every number below comes from
`results/filters.json` / `results/filters.md`, written by:

```bash
python scripts/benchmark_filters.py --full-check --end-to-end
```

## 1. Why it matters

Filtering itself is cheap. The real cost is in week 9: to choose a guess, the
entropy agent must know how *every* allowed guess would split the current
candidates. At the first turn that is 5,370 guesses × 1,900 answers =
**10,203,000 feedback evaluations**, and again at every later turn on the
remaining candidates.

| Way to get the patterns of one turn | Measured cost |
| --- | ---: |
| Scalar `feedback()` (1.06 µs per call), all 10,203,000 pairs | **10.0 s** |
| Pattern table: `partition_counts` for all 5,370 guesses | **38.1 ms** |
| Building the pattern table once (vectorised numpy) | 2.52 s |
| Loading the cached table | 1.2 ms |

With scalar feedback, a single turn of the entropy agent on the full answer
list costs about 10 seconds, which is far too slow to evaluate 1,900 games or
to answer interactively. With the table the same turn takes milliseconds. The
table costs 10.2 MB (one `uint8` per cell) and is built once and cached.

## 2. Constraints derived from feedback

`wordle_tr/constraints.py`. One observation (guess g, pattern p) gives four
kinds of constraint on the hidden word:

| Kind | Rule | KAPAK → KALEM 🟩🟩⬜⬜⬜ |
| --- | --- | --- |
| Fixed letter | green at i → letter g_i at position i | position 1 = K, position 2 = A |
| Forbidden letter | yellow or grey at i → g_i is not at position i | P not at 3, A not at 4, K not at 5 |
| Minimum count | k_L = number of green + yellow copies of L in g → L appears ≥ k_L times | K ≥ 1, A ≥ 1 |
| Exact count | some copy of L is grey → L appears exactly k_L times (k_L = 0: absent) | K = 1, A = 1, P = 0 |

`describe()` turns this into English:
`Letter 1 is K; letter 2 is A; not in word: P; A is not elsewhere; K is not elsewhere`.

**Several observations** combine per quantity. The fixed letters and the
forbidden sets are united. For each letter, the bounds are the **maximum of
the minimums** and the **minimum of the maximums**. Each observation only
bounds the same quantities (the letter at a position, the number of copies of
a letter), so the merged constraints hold exactly when every single
observation's constraints hold.

**Contradictions** raise `ContradictionError` (a `ValueError`) and leave the
object unchanged:

* two different fixed letters at one position;
* a fixed letter that is also forbidden there;
* a minimum above a maximum;
* more than 5 required letters;
* an empty domain;
* a required letter with no position left for it;
* an **impossible pattern**, where a yellow copy of a letter comes after a grey
  copy of the same letter (yellows always go to the left-most copies, see
  section 3).

`Constraints.domains()` gives the letters still allowed at each position
(node consistency).

## 3. Proof: the constraints are exactly the feedback

**Notation.** For a word x and a letter L, n_x(L) is the number of copies of L
in x. f(g, w) is the feedback of guess g against word w (week 7). For an
observation (g, p) with colours c_1..c_5:

* k_L is the number of positions i with g_i = L and c_i ≠ grey;
* the constraints C(g, p) are the four kinds of section 2:
  * (C1) w_i = g_i where c_i is green;
  * (C2) w_i ≠ g_i where c_i is not green;
  * (C3) n_w(L) ≥ k_L;
  * (C4) n_w(L) = k_L if L has a grey copy in p.

**Lemma 1 (counts).** In f(g, w), for every letter L, the number of green plus
yellow copies of L equals min(n_g(L), n_w(L)).

*Proof.* Let G_L be the number of positions with g_i = w_i = L (the greens of
L). After the green pass, the word w has u_L = n_w(L) − G_L copies of L at
non-green positions (its *unmatched* copies). The guess has n_g(L) − G_L
non-green copies of L. The yellow pass scans these from left to right and
colours one yellow for each unmatched copy still unused, so the number of
yellows is Y_L = min(n_g(L) − G_L, n_w(L) − G_L) = min(n_g(L), n_w(L)) − G_L.
Hence G_L + Y_L = min(n_g(L), n_w(L)). ∎

**Lemma 2 (positions).** In f(g, w), the yellow copies of L are the first
Y_L non-green copies of L in g, counting from the left. All later non-green
copies are grey.

*Proof.* The yellow pass goes from left to right, and the number of unused
unmatched copies only decreases. Once a copy is grey (none left), every later
copy is grey too. ∎

**Theorem.** Let p be a real pattern, p = f(g, s) for some word s. Then for every word w:

  w satisfies C(g, p) ⇔ f(g, w) = p.

*Proof of ⇐.* Suppose f(g, w) = p.

* The greens of f(g, w) are exactly the positions where g_i = w_i, so C1 and
  C2 hold.
* By Lemma 1, k_L = min(n_g(L), n_w(L)) ≤ n_w(L), so C3 holds.
* If L has a grey copy in p, not all n_g(L) copies are green or yellow, so
  k_L < n_g(L). Then min(n_g(L), n_w(L)) = k_L forces n_w(L) = k_L, so C4
  holds.

*Proof of ⇒.* Suppose w satisfies C1–C4. Let q = f(g, w) with colours d_i.

1. **Same greens.** If c_i is green, C1 gives w_i = g_i, so d_i is green. If c_i
   is not green, C2 gives w_i ≠ g_i, so d_i is not green.
2. **Same number of green + yellow copies of each letter.** By Lemma 1 for q,
   this number is min(n_g(L), n_w(L)). By Lemma 1 for p = f(g, s), it is
   k_L = min(n_g(L), n_s(L)).
   - If L has a grey copy in p, then k_L < n_g(L), and C4 gives n_w(L) = k_L.
     So min(n_g(L), n_w(L)) = k_L.
   - Otherwise every copy of L is green or yellow in p, so k_L = n_g(L). C3
     gives n_w(L) ≥ n_g(L), so min(n_g(L), n_w(L)) = n_g(L) = k_L.

   With step 1, the number of **yellow** copies Y_L is also the same in p and
   q.
3. **Same positions.** Both p and q are real feedback, so by Lemma 2 the yellow
   copies of L are the first Y_L non-green copies of L in g in both. The greens
   are the same (step 1) and so is Y_L (step 2), so p and q have the same yellows
   and the same greys: f(g, w) = p. ∎

The theorem needs p to be real. For example, KAPAK with a grey first A and a
yellow second A satisfies C1–C4 for some words, but no word ever produces
that pattern (Lemma 2). This is why `Constraints` rejects such input as
impossible.

**Corollary.** For a history of real observations, w is consistent with all
of them ⇔ w satisfies the merged constraints (section 2). Filtering with
constraints is therefore exact. The tests check this against the reference
filter on 300 random histories and on 15,000 random (guess, answer) pairs.

## 4. The CSP model

| CSP element | In Wordle |
| --- | --- |
| Variables | X1..X5, the letters of the hidden word |
| Domains | D_i ⊆ the 29 letters: {L} if position i is fixed, otherwise all letters minus the ones forbidden at i and the absent ones (`Constraints.domains()`, node consistency) |
| Unary constraints | fixed and forbidden letters, already applied to the domains |
| Global constraints | lo_L ≤ #{i : X_i = L} ≤ hi_L for every letter with a known bound (minimum and exact counts) |
| Dictionary constraint | X1..X5 must spell a word of the answer list, enforced by searching inside a trie |
| Solution | every assignment that satisfies all constraints = the candidate set |

## 5. Trie, backtracking and forward checking

`wordle_tr/csp_solver.py`. The **trie** stores the 1,900 answers as paths of
5 letters, with children in Turkish alphabetical order. It has **4,932 nodes**.
Searching *inside* the trie means a prefix that starts no answer is never
extended, so the dictionary constraint costs nothing extra. Because the
children are ordered, the solutions come out in Turkish alphabetical order,
just like the other filters.

**Backtracking** assigns X1, X2, … from left to right. At each trie node it
tries only the children whose letter is in the position's domain. Each
assignment tried is one *node expanded*.

**Forward checking**, after assigning X_p = c, prunes the branch when:

1. a letter's maximum count would be exceeded (when c reaches hi_c, c leaves
   all later domains, and a later domain that becomes empty prunes the branch);
2. the letters still required do not fit: for some letter L, more copies are
   needed (lo_L − count_L) than there are later positions whose domain allows L,
   or the total number of missing letters exceeds the number of positions left.

```text
BACKTRACK(node, p):
    if p = 5: record the word; return
    for each child letter c of node with c ∈ D_p and count(c) < hi_c:
        X_p ← c; count(c) += 1
        if FORWARD-CHECK(p + 1, c): BACKTRACK(child, p + 1)
        count(c) −= 1
```

Without forward checking, the count constraints are only checked on complete
words. On the 500 benchmark states:

| Search | Mean nodes expanded | Trie nodes |
| --- | ---: | ---: |
| Backtracking only | 709.5 | 4,932 |
| Backtracking + forward checking | **614.6** | 4,932 |

Node consistency and the trie already remove most of the space, because a
handful of grey letters shrinks every domain. Forward checking then cuts the
branches where the yellow letters can no longer fit, such as KEMER after
"KE" when two A's are still needed (see `tests/test_week8.py`). In the game
loop, the CSP filter solves the CSP of the whole history at every turn, so
the search gets smaller as constraints accumulate.

## 6. The pattern table

`wordle_tr/pattern_table.py` precomputes **M[g, a] = feedback(g, a)** for all
5,370 guesses × 1,900 answers as `uint8` (10,203,000 cells, 10.2 MB).

**Vectorised computation.** The table is computed with numpy, in chunks of
256 guesses, without a Python loop over pairs. For each (guess, answer) pair,
two 5 × 5 letter-equality matrices give everything:

* `equal[i, j]`: guess letter i = answer letter j. Its diagonal gives the
  **greens**.
* `same[i, k]` for k < i: guess letter k is an earlier copy of guess letter i.

**Yellow rule as counts.** A non-green position i with letter L is yellow
**iff** the number of L's among the answer's non-green positions is greater
than the number of non-green L's in the guess before i:

  yellow_i = ¬green_i ∧ Σ_j equal[i, j]·¬green_j > Σ_{k<i} same[i, k]·¬green_k

By Lemma 2, the non-green copies of L become yellow from left to right as long
as unmatched copies remain, so this is exactly the two-pass rule. Example,
TATLI → OTLAK: OTLAK has one non-green T. The first T (position 1) has no
earlier non-green T, and 1 > 0, so it is yellow. The second T (position 3) has
one earlier non-green T, and 1 > 1 is false, so it is grey. Result: 🟨🟨⬜🟨⬜.
The pattern number is Σ_i (2·green_i + yellow_i)·3^(4−i), as in week 7.

**Cache.** The table is saved as `data/cache/pattern_table_<hash>.npy`, where
the hash is computed from both word lists. Changing a list changes the file
name, so the table is rebuilt. The cache is git-ignored.

**API**

| Method | Purpose |
| --- | --- |
| `pattern(g, a)` | one lookup (ids or words) |
| `all_ids()` | answer ids 0..1,899 |
| `filter_ids(ids, g, p)` | the one-line filter `ids[M[g, ids] == p]` |
| `filter_words(words, g, p)` | the same filter, on words |
| `partition_counts(g, ids)` | `np.bincount(M[g, ids], minlength=243)`: how the candidates split over the 243 patterns |

## 7. Benchmark

`wordle_tr/filters.py` puts the four methods behind one interface,
`filter_fn(candidates, history)`. It returns the candidates that are
consistent with every observation, in the same order. The benchmark draws
500 random game states (seed 1234), each a hidden answer and 1–4 random
guesses. It computes each state's candidates from all 1,900 answers with each
method and keeps the fastest of 3 runs. On average 71.6 candidates remain.

| Method | Mean ms / state | Median ms | Speed-up vs reference |
| --- | ---: | ---: | ---: |
| feedback (reference) | 2.054 | 1.930 | 1.0× |
| constraints | 0.390 | 0.349 | 5.3× |
| csp | 0.502 | 0.323 | 4.1× |
| table | 0.017 | 0.015 | 118.1× |
| table (ids only, no word conversion) | 0.012 | 0.012 | 174.5× |

* **Agreement:** all four methods returned identical candidate sets in all
  500 states.
* **Full check:** every one of the 10,203,000 table cells equals scalar
  `feedback()` (0 mismatches).
* **End to end:** the letter-frequency agent on all 1,900 answers plays
  identical games with every filter:

| Filter | Total s | Filtering s | Mean guesses |
| --- | ---: | ---: | ---: |
| feedback | 4.40 | 3.98 | 3.7400 |
| constraints | 1.78 | 1.34 | 3.7400 |
| csp | 3.31 | 2.86 | 3.7400 |
| table | 0.51 | 0.10 | 3.7400 |

**Comparison with the previous build** (reference ≈ 8 ms per filter;
constraints ≈ 4.5×, CSP ≈ 6.7× and table ≈ 300× faster; table built in
≈ 4 s, loaded in ≈ 0.01 s):

* **Constraints:** 5.3× faster than the reference, a little above the previous
  ≈ 4.5×.
* **Table and CSP:** smaller speed-ups (118× for the table, 4.1× for the CSP).
  Our reference filter is much faster than before (2.054 ms instead of
  ≈ 8 ms) because `feedback()` costs only 1.06 µs per call, so the same
  absolute times give smaller ratios.
* **Building and loading:** the table builds in 2.52 s and loads in 1.2 ms.

The CSP is the slowest of the new methods in pure Python, since every node
costs interpreter work. Its value here is conceptual: it is the same problem
seen as a CSP, it is provably exact, and its search effort can be measured.

## 8. Bridge to week 9

The entropy agent needs, at every turn and for every allowed guess, the
distribution of patterns over the current candidates. With the table this is
`partition_counts(g, ids)`: one `bincount` per guess. For all 5,370 guesses
over all 1,900 answers it costs 38.1 ms, against 10.0 s with scalar feedback.
The agent receives a `PatternTable` at construction and keeps the week 7
interface; the game loop can use the `table` filter.
