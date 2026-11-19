"""Week 10: exact oracle and expectimax agent."""

from __future__ import annotations

import numpy as np
import pytest

from wordle_tr.agents import ExpectimaxAgent, make_agent
from wordle_tr.feedback import feedback
from wordle_tr.oracle import Oracle, distinct_splits, lower_bound, opener_lower_bound, parts_bound, policy_value
from wordle_tr.pattern_table import PatternTable, compute_pattern_matrix
from wordle_tr.simulate import random_histories

SA_MA = ["saçma", "sanma", "sapma", "savma"]


def tiny_table(guesses: list[str], answers: list[str]) -> PatternTable:
    return PatternTable(guesses, answers, compute_pattern_matrix(guesses, answers))


def sets_from_states(table, answers, guesses, low: int, high: int, count: int, seed: int) -> list[np.ndarray]:
    found: dict[bytes, np.ndarray] = {}
    for _, history in random_histories(answers, guesses, 50 * count, seed):
        ids = table.all_ids()
        for guess, pattern in history:
            ids = table.filter_ids(ids, guess, pattern)
        if low <= len(ids) <= high:
            found.setdefault(ids.tobytes(), ids)
        if len(found) == count:
            break
    return list(found.values())


# --------------------------------------------------------------------------- oracle, by hand


def test_oracle_one_and_two_candidates():
    table = tiny_table(["kalem", "kalın"], ["kalem", "kalın"])
    oracle = Oracle(table)
    assert oracle.solve(["kalem"]) == (1.0, "kalem")
    assert oracle.solve(["kalem", "kalın"])[0] == 1.5  # guess one: 1 or 2 guesses


def test_oracle_candidate_that_separates_the_rest():
    # KALEM gives three different patterns on these three words: 1 + 2/3 * 1 = 5/3.
    words = ["kalem", "kalın", "kayak"]
    value, guess = Oracle(tiny_table(words, words)).solve(words)
    assert value == pytest.approx(5 / 3) and guess == "kalem"


def test_oracle_one_letter_family_with_candidates_only():
    # Each candidate guess only tests itself, so the words take 1, 2, 3 and 4 guesses: mean 2.5.
    value, _ = Oracle(tiny_table(SA_MA, SA_MA)).solve(SA_MA)
    assert value == pytest.approx(2.5)


def test_oracle_prefers_a_non_candidate_that_splits_the_family():
    # AVUNÇ gives four different patterns (it tests Ç, N and V at once): 1 + 1 = 2 guesses.
    table = tiny_table(["avunç"] + SA_MA, SA_MA)
    assert len({feedback("avunç", w) for w in SA_MA}) == 4
    assert Oracle(table).solve(SA_MA) == (pytest.approx(2.0), "avunç")


def test_distinct_splits_merge_equivalent_guesses():
    table = tiny_table(["avunç", "kalem", "kayak"] + SA_MA, SA_MA)
    options = distinct_splits(table.matrix, table.all_ids())
    signatures = {tuple(sorted(tuple(p) for p in parts)) for _, _, parts in options}
    assert len(signatures) == len(options)  # KALEM and KAYAK split SA_MA the same way (no information)
    assert all(sum(len(p) for p in parts) <= 4 for _, _, parts in options)


# --------------------------------------------------------------------------- oracle on real subsets


def test_lower_bounds_hold(table, answers, guesses):
    oracle = Oracle(table)
    for ids in sets_from_states(table, answers, guesses, 3, 25, 30, seed=5):
        v = oracle.value(ids)
        assert v >= lower_bound(len(ids)) - 1e-12
        assert v >= parts_bound(table.matrix, ids, oracle.answer_rows) - 1e-12


def test_opener_lower_bound(table):
    bound, opener = opener_lower_bound(table)
    assert 2.0 < bound < 3.4 and opener in table.guess_index


def test_full_width_expectimax_equals_the_oracle(table, answers, guesses):
    oracle = Oracle(table)
    agent = ExpectimaxAgent(table, depth=6, width=None)
    for ids in sets_from_states(table, answers, guesses, 3, 8, 15, seed=7):
        exact = oracle.value(ids)
        value, _ = agent.search(ids, 6)
        assert value == pytest.approx(exact, abs=1e-9)
        assert policy_value(agent, table, ids) == pytest.approx(exact, abs=1e-9)


# --------------------------------------------------------------------------- expectimax agent


def test_registry_and_options(table):
    agent = make_agent("expectimax", table=table, depth=1, width=5)
    assert isinstance(agent, ExpectimaxAgent) and agent.depth == 1 and agent.width == 5
    assert make_agent("expectimax", table=table).depth == 2
    with pytest.raises(ValueError):
        ExpectimaxAgent(table, depth=0)


@pytest.mark.parametrize("depth", [1, 2])
def test_expectimax_is_never_worse_than_entropy_in_expectation(table, answers, guesses, depth):
    """Rollout: the entropy choice is in the beam and the leaves are entropy values."""
    entropy = make_agent("entropy", table=table)
    agent = ExpectimaxAgent(table, depth=depth, width=10)
    for ids in sets_from_states(table, answers, guesses, 3, 80, 25, seed=11):
        mine, base = policy_value(agent, table, ids), policy_value(entropy, table, ids)
        assert mine <= base + 1e-9
        assert mine <= agent.search(ids, depth)[0] + 1e-9  # replanning never hurts the plan


def test_policy_value_equals_playing_every_word(table, answers, guesses):
    agent = make_agent("entropy", table=table)
    ids = sets_from_states(table, answers, guesses, 20, 60, 1, seed=3)[0]
    words = table.words(ids)
    total = 0
    for secret in words:
        candidates, n = words, 0
        while True:
            n += 1
            guess = agent.choose_guess([], candidates)
            if guess == secret:
                break
            candidates = [w for w in candidates if feedback(guess, w) == feedback(guess, secret)]
        total += n
    assert policy_value(agent, table, ids) == pytest.approx(total / len(words))


def test_expectimax_plays_and_caches_its_opening(table, answers):
    agent = ExpectimaxAgent(table, depth=1, width=5)
    first = agent.choose_guess([], answers)
    nodes = agent.nodes
    assert agent.choose_guess([], answers) == first and agent.nodes == nodes
    assert first in table.guess_index
    assert agent.last_choice["expected_guesses"] < 3.5
    candidates = [w for w in answers if feedback(first, w) == feedback(first, "sayma")]
    assert agent.choose_guess([(first, feedback(first, "sayma"))], candidates) in table.guess_index
