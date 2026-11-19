"""Week 9: entropy (information-gain) agents."""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pytest

from wordle_tr.agents import AGENTS, EntropyAgent, LetterFrequencyAgent, make_agent
from wordle_tr.agents.entropy import entropy_bits, frequency_prior, partition_stats
from wordle_tr.feedback import feedback
from wordle_tr.filters import make_filter
from wordle_tr.simulate import evaluate, summarize
from wordle_tr.words import load_frequencies

VARIANTS = ["entropy", "entropy_candidates", "entropy_freq", "most_parts"]


@pytest.fixture(scope="module")
def table_filter(answers, guesses, table):
    return make_filter("table", answers, guesses, table)


@pytest.fixture(scope="module")
def full_runs(answers, guesses, table, table_filter):
    """Every answer played by the entropy and letter-frequency agents (unlimited guesses)."""
    return {name: evaluate(agent, answers, guesses, table_filter)
            for name, agent in [("entropy", make_agent("entropy", table=table)),
                                ("frequency", LetterFrequencyAgent())]}


def test_entropy_of_known_partitions():
    assert entropy_bits([5]) == 0.0
    assert entropy_bits([1, 1]) == pytest.approx(1.0)
    assert entropy_bits([1, 1, 1, 1]) == pytest.approx(2.0)
    assert entropy_bits([4, 1]) == pytest.approx(-(0.8 * math.log2(0.8) + 0.2 * math.log2(0.2)))
    assert entropy_bits([2, 1, 1, 1]) == pytest.approx(math.log2(5) - 2 / 5)  # log2 n - sum(c log2 c) / n
    assert entropy_bits([0, 3, 0, 3]) == pytest.approx(1.0)  # empty parts do not count


def test_partition_stats_match_scalar_feedback(table, guesses, answers):
    rng = np.random.default_rng(11)
    prior = frequency_prior(answers, load_frequencies())
    for n in (3, 40, 400):
        ids = np.sort(rng.choice(len(answers), n, replace=False))
        rows = rng.choice(len(guesses), 25, replace=False)
        bits, parts = partition_stats(table.matrix, ids, rows)
        wbits, _ = partition_stats(table.matrix, ids, rows, prior[ids])
        for k, g in enumerate(rows):
            patterns = [feedback(guesses[g], answers[i]) for i in ids]
            sizes = Counter(patterns)
            weights = Counter()
            for p, i in zip(patterns, ids):
                weights[p] += prior[i]
            assert bits[k] == pytest.approx(entropy_bits(list(sizes.values())), abs=1e-9)
            assert parts[k] == len(sizes)
            assert wbits[k] == pytest.approx(entropy_bits(list(weights.values())), abs=1e-9)


def test_registry_has_all_variants(table):
    assert set(VARIANTS) <= set(AGENTS)
    for name in VARIANTS:
        agent = make_agent(name, table=table)
        assert isinstance(agent, EntropyAgent) and agent.name == name


@pytest.mark.parametrize("name", VARIANTS)
def test_agents_return_allowed_words(name, table, guesses, answers, random_histories):
    agent = make_agent(name, table=table)
    guess_set = set(guesses)
    for _, history in random_histories[:60]:
        candidates = [w for w in answers if all(feedback(g, w) == p for g, p in history)]
        guess = agent.choose_guess(history, candidates)
        assert guess in guess_set
        if name == "entropy_candidates" or len(candidates) <= 2:
            assert guess in candidates


def test_ties_prefer_candidates_then_turkish_order(table):
    # KALEM and KALIN split these three apart, and so do many non-candidates that come
    # earlier in the alphabet (e.g. ABACI); the agent must pick the first candidate.
    agent = make_agent("entropy", table=table)
    assert agent.choose_guess([], ["kalem", "kalın", "kayak"]) == "kalem"
    assert agent.last_choice["bits"] == pytest.approx(math.log2(3))
    assert agent.rank(table.answer_ids(["kalem", "kalın", "kayak"]), 3)[1]["guess"] == "kalın"


def test_two_candidates_left(table, answers):
    assert make_agent("entropy", table=table).choose_guess([], ["saçma", "sayma"]) == "saçma"
    prior_agent = make_agent("entropy_freq", table=table)
    frequencies = load_frequencies()
    expected = max(["saçma", "sayma"], key=lambda w: frequencies[w])
    assert prior_agent.choose_guess([], ["saçma", "sayma"]) == expected


def test_first_guess_is_cached(table, answers):
    agent = make_agent("entropy", table=table)
    first = agent.choose_guess([], answers)
    assert agent.searches == 1
    assert agent.choose_guess([], answers) == first and agent.searches == 1
    assert first == agent.rank(table.all_ids(), 1)[0]["guess"]


def test_most_parts_opener_has_the_most_parts(table):
    ids = table.all_ids()
    best = make_agent("most_parts", table=table).rank(ids, 1)[0]
    entropy_best = make_agent("entropy", table=table).rank(ids, 1)[0]
    assert best["parts"] >= entropy_best["parts"]
    assert entropy_best["bits"] >= best["bits"]


def test_frequency_prior(answers):
    frequencies = load_frequencies()
    prior = frequency_prior(answers, frequencies)
    assert prior.shape == (len(answers),) and np.all((prior > 0) & (prior < 1))
    by_count = sorted(range(len(answers)), key=lambda i: -frequencies[answers[i]])
    assert prior[by_count[0]] > 0.95 and prior[by_count[-1]] < 0.3
    assert np.all(np.diff(prior[by_count]) <= 0)  # more frequent, more weight


def test_entropy_is_deterministic(table, answers, guesses, table_filter):
    words = answers[::50]
    first = [r.guesses for r in evaluate(make_agent("entropy", table=table), answers, guesses, table_filter,
                                         words=words)]
    second = [r.guesses for r in evaluate(make_agent("entropy", table=table), answers, guesses, table_filter,
                                          words=words)]
    assert first == second


def test_entropy_solves_every_answer(full_runs):
    results = full_runs["entropy"]
    assert all(r.solved and r.guesses[-1] == r.answer for r in results)


def test_entropy_beats_letter_frequency_on_the_full_list(full_runs):
    entropy = summarize(full_runs["entropy"])
    frequency = summarize(full_runs["frequency"])
    assert entropy.mean <= frequency.mean
    assert entropy.failures <= frequency.failures


@pytest.mark.parametrize("name", ["entropy_candidates", "entropy_freq", "most_parts"])
def test_variants_solve_a_sample(name, table, answers, guesses, table_filter):
    words = answers[::40]
    results = evaluate(make_agent(name, table=table), answers, guesses, table_filter, words=words)
    assert all(r.solved for r in results)
