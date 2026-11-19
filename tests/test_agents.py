"""Week 7: agent interface, baseline agents and the evaluation loop."""

from __future__ import annotations

import random

import pytest

from wordle_tr.agents import AGENTS, Agent, LetterFrequencyAgent, RandomAgent, make_agent
from wordle_tr.feedback import ALL_GREEN, feedback
from wordle_tr.simulate import GameResult, aggregate, evaluate, play_game, summarize


@pytest.fixture(scope="module")
def sample(answers) -> list[str]:
    return random.Random(1234).sample(answers, 100)


def test_registry():
    assert {"random", "frequency"} <= set(AGENTS)
    assert isinstance(make_agent("random", seed=3), RandomAgent)
    assert isinstance(make_agent("frequency"), LetterFrequencyAgent)
    with pytest.raises(ValueError):
        make_agent("no-such-agent")


@pytest.mark.parametrize("name", ["random", "frequency"])
def test_agents_solve_a_sample_and_only_guess_candidates(name, answers, guesses, sample):
    answer_set = set(answers)
    results = evaluate(make_agent(name, seed=1), answers, guesses, words=sample)
    assert len(results) == len(sample)
    for r in results:
        assert r.solved and r.guesses[-1] == r.answer and r.patterns[-1] == ALL_GREEN
        assert all(g in answer_set for g in r.guesses)
        assert r.candidates_after[-1] == 1
        assert r.candidates_after == sorted(r.candidates_after, reverse=True)


def test_frequency_agent_first_guess_and_determinism(answers, guesses, sample):
    agent = LetterFrequencyAgent()
    assert agent.choose_guess([], answers) == "erika"
    first = [r.guesses for r in evaluate(agent, answers, guesses, words=sample)]
    second = [r.guesses for r in evaluate(LetterFrequencyAgent(), answers, guesses, words=sample)]
    assert first == second


def test_frequency_agent_scores_distinct_letters():
    # letters in how many words: a 3, k 2, others 1. kalem = 2+3+1+1+1 = 8, kayak = 2+3+1 = 6,
    # araba = 3+1+1 = 5 (repeated letters count once)
    assert LetterFrequencyAgent().choose_guess([], ["kayak", "kalem", "araba"]) == "kalem"
    # ties go to Turkish alphabetical order: c < ç < d and ı < i
    assert LetterFrequencyAgent().choose_guess([], ["dalım", "çalım", "calım"]) == "calım"
    assert LetterFrequencyAgent().choose_guess([], ["ilgin", "ılgın"]) == "ılgın"


def test_random_agent_is_reproducible_by_seed(answers, guesses, sample):
    words = sample[:30]
    run = lambda seed: [r.guesses for r in evaluate(RandomAgent(seed), answers, guesses, words=words)]
    assert run(7) == run(7)
    assert run(7) != run(8)


def test_play_game_reports_every_turn(answers, guesses):
    seen = []
    result = play_game(LetterFrequencyAgent(), "sayma", answers, guesses,
                       on_turn=lambda turn, g, p, c: seen.append((turn, g, p, len(c))))
    assert [s[0] for s in seen] == list(range(1, result.num_guesses + 1))
    assert [s[3] for s in seen] == result.candidates_after
    assert result.patterns == [feedback(g, "sayma") for g in result.guesses]
    assert len(result.guess_times) == len(result.filter_times) == result.num_guesses


def test_play_game_respects_the_guess_limit(answers, guesses):
    result = play_game(LetterFrequencyAgent(), "sayma", answers, guesses, max_guesses=6)
    assert not result.solved and result.num_guesses == 6


def test_agent_cannot_change_the_game_history(answers, guesses):
    class Vandal(Agent):
        def choose_guess(self, history, candidates):
            history.append(("zzzzz", 0))
            return candidates[0]

    result = play_game(Vandal(), "kalem", answers, guesses)
    assert result.solved and "zzzzz" not in result.guesses


def fake(answer: str, n: int, solved: bool = True) -> GameResult:
    return GameResult(answer=answer, guesses=["x"] * n, patterns=[0] * n, candidates_after=[1] * n,
                      guess_times=[0.001] * n, filter_times=[0.002] * n, solved=solved)


def test_summarize_fields():
    results = [fake("kalem", 3), fake("sayma", 8), fake("erika", 1), fake("yazma", 8), fake("kayak", 5)]
    s = summarize(results, "test", limit=6, hardest=3)
    assert s.agent == "test" and s.games == 5
    assert s.mean == pytest.approx(5.0)
    assert s.within_limit_pct == pytest.approx(60.0) and s.failures == 2
    assert s.max == 8
    assert s.histogram == {1: 1, 3: 1, 5: 1, 8: 2}
    assert s.hardest == [("sayma", 8), ("yazma", 8), ("kayak", 5)]
    assert s.mean_time_per_guess_ms == pytest.approx(1.0)
    assert s.mean_filter_time_ms == pytest.approx(2.0)
    assert s.total_time_s == pytest.approx(25 * 0.003)
    assert s.to_dict()["histogram"] == {"1": 1, "3": 1, "5": 1, "8": 2}


def test_unsolved_games_count_as_failures():
    s = summarize([fake("kalem", 6, solved=False), fake("erika", 2)], limit=6)
    assert s.failures == 1 and s.within_limit_pct == pytest.approx(50.0)


def test_aggregate_over_seeds():
    runs = [summarize([fake("kalem", 3), fake("erika", 5)]), summarize([fake("kalem", 4), fake("erika", 6)])]
    a = aggregate(runs)
    assert a["runs"] == 2
    assert a["mean"] == pytest.approx(4.5)
    assert a["mean_std"] == pytest.approx(0.7071, abs=1e-4)
    assert a["histogram"] == {"3": 0.5, "4": 0.5, "5": 0.5, "6": 0.5}
