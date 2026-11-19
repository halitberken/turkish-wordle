"""Week 8: constraints, CSP solver, pattern table and the four filters."""

from __future__ import annotations

import random

import pytest

import numpy as np

from wordle_tr.alphabet import ALPHABET, normalize
from wordle_tr.constraints import Constraints, ContradictionError
from wordle_tr.csp_solver import CSPSolver, WordTrie
from wordle_tr.feedback import ALL_GREEN, NUM_PATTERNS, feedback, filter_candidates, is_consistent, parse_pattern
from wordle_tr.filters import FILTER_NAMES, filter_constraints, filter_reference, make_filter
from wordle_tr.pattern_table import PatternTable, compute_pattern_matrix, lists_hash


def test_constraints_match_the_reference_filter_on_random_histories(random_histories, answers):
    for answer, history in random_histories:
        constraints = Constraints.from_history(history)
        by_constraints = [w for w in answers if constraints.is_satisfied(w)]
        assert by_constraints == [w for w in answers if is_consistent(w, history)]
        assert answer in by_constraints


def test_single_observation_equivalence_on_random_pairs(guesses, answers):
    """For a real pattern p = f(g, s): w satisfies the constraints of (g, p) <=> f(g, w) = p."""
    rng = random.Random(2024)
    for _ in range(15_000):
        g, s = rng.choice(guesses), rng.choice(answers)
        p = feedback(g, s)
        constraints = Constraints.from_history([(g, p)])
        assert constraints.is_satisfied(s)
        for w in rng.sample(answers, 5):
            assert constraints.is_satisfied(w) == (feedback(g, w) == p)


def reference_candidates(answers, history):
    return filter_reference(answers, history)


# --------------------------------------------------------------------------- CSP


def test_trie():
    trie = WordTrie(["kalem", "kalın", "çalım", "calım", "kayak"])
    assert trie.words() == ["calım", "çalım", "kalem", "kalın", "kayak"]
    assert "kalın" in trie and "kalıp" not in trie and "kal" in trie
    assert trie.size == 5 + 5 + 10  # calım, çalım, k-a-{l-{e-m, ı-n}, y-a-k}
    assert trie.size == len({w[:i] for w in trie.words() for i in range(1, 6)})


def test_csp_matches_the_reference(random_histories, answers, solver):
    for answer, history in random_histories:
        constraints = Constraints.from_history(history)
        expected = reference_candidates(answers, history)
        with_fc = solver.solve(constraints)
        without_fc = solver.solve(constraints, forward_checking=False)
        assert with_fc.solutions == expected == without_fc.solutions
        assert answer in with_fc.solutions
        assert with_fc.nodes_expanded <= without_fc.nodes_expanded <= solver.trie.size


def test_csp_without_constraints_returns_every_answer(answers, solver):
    result = solver.solve(Constraints())
    assert result.solutions == answers
    assert result.nodes_expanded == solver.trie.size


def test_forward_checking_prunes_required_letters():
    # ARABA against KAPAK: exactly two A's, not as letter 1, 3 or 5. After K-E only letters
    # 3-5 are left and just one of them allows A, so forward checking cuts KEMER at "ke".
    solver = CSPSolver(["kalem", "kayak", "kapak", "kazak", "kemer"])
    constraints = Constraints.from_history([("araba", feedback("araba", "kapak"))])
    fc, bt = solver.solve(constraints), solver.solve(constraints, forward_checking=False)
    assert fc.solutions == bt.solutions == ["kapak", "kayak", "kazak"]
    assert fc.nodes_expanded < bt.nodes_expanded


# --------------------------------------------------------------------------- pattern table

TRICKY_GUESSES = ["kapak", "ekler", "tatlı", "kekik", "alaka", "aaaaa", "kalem", "üzgün", "sayma", "ılgın"]
TRICKY_ANSWERS = ["kalem", "otlak", "kayak", "kapak", "aaaaa", "saçma", "ilgin", "ılgın", "araba"]


def test_pattern_matrix_on_tricky_duplicate_cases():
    matrix = compute_pattern_matrix(TRICKY_GUESSES, TRICKY_ANSWERS)
    for i, g in enumerate(TRICKY_GUESSES):
        for j, a in enumerate(TRICKY_ANSWERS):
            assert matrix[i, j] == feedback(g, a), (g, a)
    table = PatternTable(TRICKY_GUESSES, TRICKY_ANSWERS, matrix)
    assert table.pattern("kapak", "kalem") == parse_pattern("ggxxx")
    assert table.pattern("ekler", "kalem") == parse_pattern("xyggx")
    assert table.pattern("tatlı", "otlak") == parse_pattern("yyxyx")
    assert table.pattern(normalize("KEKİK"), "kayak") == parse_pattern("gxxxg")
    assert table.pattern("alaka", "kapak") == parse_pattern("yxyyx")
    assert table.pattern("ılgın", "ilgin") == parse_pattern("xggxg")  # ı and i are different letters


def test_pattern_table_matches_scalar_feedback_on_a_sample(table, guesses, answers):
    rng = random.Random(99)
    for _ in range(20_000):
        g, a = rng.randrange(len(guesses)), rng.randrange(len(answers))
        assert table.matrix[g, a] == feedback(guesses[g], answers[a])
    assert table.matrix.dtype == np.uint8 and table.matrix.shape == (len(guesses), len(answers))
    assert table.pattern("kalem", "kalem") == ALL_GREEN


@pytest.mark.slow
def test_every_pattern_table_cell_matches_scalar_feedback(table, guesses, answers):
    for g, guess in enumerate(guesses):
        assert table.matrix[g].tolist() == [feedback(guess, a) for a in answers], guess


def test_table_filter_matches_the_reference(random_histories, answers, table):
    for _, history in random_histories:
        ids = table.all_ids()
        for guess, pattern in history:
            ids = table.filter_ids(ids, guess, pattern)
        assert table.words(ids) == reference_candidates(answers, history)
        guess, pattern = history[0]
        assert table.filter_words(answers, guess, pattern) == filter_candidates(answers, guess, pattern)


def test_partition_counts_sum_to_the_candidate_count(random_histories, table):
    rng = random.Random(3)
    for _, history in random_histories[:50]:
        ids = table.all_ids()
        for guess, pattern in history:
            ids = table.filter_ids(ids, guess, pattern)
        for g in rng.sample(range(len(table.guesses)), 20):
            counts = table.partition_counts(g, ids)
            assert counts.shape == (NUM_PATTERNS,) and counts.sum() == len(ids)
            p = int(np.argmax(counts))
            assert counts[p] == len(table.filter_ids(ids, g, p))


def test_table_cache_is_reused_and_keyed_by_the_lists(tmp_path):
    first = PatternTable.load_or_build(TRICKY_GUESSES, TRICKY_ANSWERS, cache_dir=tmp_path)
    files = list(tmp_path.glob("pattern_table_*.npy"))
    assert [f.name for f in files] == [f"pattern_table_{lists_hash(TRICKY_GUESSES, TRICKY_ANSWERS)}.npy"]
    again = PatternTable.load_or_build(TRICKY_GUESSES, TRICKY_ANSWERS, cache_dir=tmp_path)
    assert np.array_equal(first.matrix, again.matrix)
    PatternTable.load_or_build(TRICKY_GUESSES, TRICKY_ANSWERS[:-1], cache_dir=tmp_path)  # changed list
    assert len(list(tmp_path.glob("pattern_table_*.npy"))) == 2


# --------------------------------------------------------------------------- all filters


def test_all_four_filters_agree(random_histories, answers, guesses, table):
    filters = {name: make_filter(name, answers, guesses, table) for name in FILTER_NAMES}
    for answer, history in random_histories:
        expected = reference_candidates(answers, history)
        for name, filter_fn in filters.items():
            assert filter_fn(answers, history) == expected, name  # all at once
            candidates = answers
            for k in range(1, len(history) + 1):  # step by step, as in the game loop
                candidates = filter_fn(candidates, history[:k])
            assert candidates == expected, name


def test_unknown_filter():
    with pytest.raises(ValueError):
        make_filter("no-such-filter")


def test_four_kinds_of_constraint():
    # KAPAK against KALEM: 🟩🟩⬜⬜⬜
    c = Constraints.from_history([("kapak", feedback("kapak", "kalem"))])
    assert c.fixed == ["k", "a", None, None, None]  # fixed letters
    assert c.forbidden[2] == {"p"} and c.forbidden[3] == {"a"} and c.forbidden[4] == {"k"}
    assert c.min_count == {"k": 1, "a": 1, "p": 0}  # minimum counts
    assert c.max_count == {"k": 1, "a": 1, "p": 0}  # exact counts (a grey copy exists)
    domains = c.domains()
    assert domains[0] == {"k"} and domains[1] == {"a"}
    assert domains[2] == set(ALPHABET) - {"p"}
    assert domains[3] == set(ALPHABET) - {"a", "p"}


def test_observations_combine_by_max_of_minimums_and_min_of_maximums():
    history = [(g, feedback(g, "kapak")) for g in ("kalem", "araba", "kekik")]
    assert Constraints.from_history(history[:1]).min_count["a"] == 1  # one green A, no grey A
    assert "a" not in Constraints.from_history(history[:1]).max_count
    c = Constraints.from_history(history)
    assert c.min_count["a"] == 2 and c.max_count["a"] == 2  # ARABA: two yellow A's and a grey one
    assert c.min_count["k"] == 2 and c.max_count["k"] == 2  # KEKİK: two green K's and a grey one
    assert c.is_satisfied("kapak") and not c.is_satisfied("kayık")


@pytest.mark.parametrize(
    "guess, answer, text",
    [
        ("kapak", "kalem", "Letter 1 is K; letter 2 is A; not in word: P; A is not elsewhere; K is not elsewhere"),
        ("ekler", "kalem", "Letter 3 is L; letter 4 is E; not in word: R; E is not elsewhere; "
                           "contains K, not as letter 2"),
        ("tatlı", "otlak", "Not in word: I; contains A, not as letter 2; contains L, not as letter 4; "
                           "contains T exactly once, not as letter 1 or 3"),
        ("kalem", "kayak", "Letter 1 is K; letter 2 is A; not in word: E, L, M"),
    ],
)
def test_describe(guess, answer, text):
    assert Constraints.from_history([(guess, feedback(guess, answer))]).describe() == text


def test_describe_without_information():
    assert Constraints().describe() == "Nothing known yet"


@pytest.mark.parametrize(
    "history",
    [
        [("kapak", parse_pattern("gxxyx"))],  # yellow A after a grey A cannot happen
        [("kalem", parse_pattern("ggggg")), ("kalem", parse_pattern("xxxxx"))],
        [("kalem", parse_pattern("gxxxx")), ("sayma", parse_pattern("gxxxx"))],  # letter 1 is K and S
        [("aaaaa", parse_pattern("yyyyy"))],  # five A's but none of them may be anywhere
        [("kalem", parse_pattern("yyyyy")), ("erika", parse_pattern("xxxxx"))],  # K, A, E absent and present
    ],
)
def test_contradictions_are_detected(history):
    with pytest.raises(ContradictionError):
        Constraints.from_history(history)


def test_failed_observation_leaves_constraints_unchanged():
    c = Constraints.from_history([("kalem", parse_pattern("ggggg"))])
    before = c.describe()
    with pytest.raises(ContradictionError):
        c.add_observation("kalem", parse_pattern("xxxxx"))
    assert c.describe() == before


def test_contradiction_error_is_a_value_error():
    assert issubclass(ContradictionError, ValueError)


def test_constraint_filter_matches_reference_on_one_step(answers):
    for guess, answer in [("kapak", "kalem"), ("erika", "sayma"), ("tatlı", "otlak")]:
        p = feedback(guess, answer)
        assert filter_constraints(answers, [(guess, p)]) == filter_candidates(answers, guess, p)
