"""Week 8: constraints (the CSP solver and pattern table tests are added in week 8).

`Constraints` is already used by the week 7 assist mode, so its tests start here.
"""

from __future__ import annotations

import random

import pytest

from wordle_tr.alphabet import ALPHABET
from wordle_tr.constraints import Constraints, ContradictionError
from wordle_tr.feedback import feedback, filter_candidates, is_consistent, parse_pattern
from wordle_tr.filters import FILTERS, filter_by_constraints


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


def test_filters_agree_incrementally(random_histories, answers):
    for _, history in random_histories[:100]:
        results = {}
        for name, filter_fn in FILTERS.items():
            candidates = answers
            for guess, pattern in history:
                candidates = filter_fn(candidates, guess, pattern)
            results[name] = candidates
        assert results["constraints"] == results["feedback"]


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
        assert filter_by_constraints(answers, guess, p) == filter_candidates(answers, guess, p)
