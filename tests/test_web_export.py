"""Phase 8: the data exported for the web demo (web/public/data/)."""

from __future__ import annotations

import json

import pytest

from wordle_tr import RESULTS_DIR, ROOT_DIR
from wordle_tr.agents import make_agent
from wordle_tr.constraints import Constraints
from wordle_tr.feedback import feedback, pattern_to_emoji

DATA = ROOT_DIR / "web" / "public" / "data"
FILES = ["guesses.json", "answers.json", "openers.json", "feedback_fixtures.json", "agent_fixtures.json",
         "summary.json"]


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", FILES)
def test_exported_files_exist_and_are_valid_json(name):
    assert (DATA / name).is_file()
    load(name)


def test_word_lists_match(guesses, answers):
    assert load("guesses.json") == guesses
    assert load("answers.json") == answers


def test_openers_match_the_python_agents(answers, table):
    openers = load("openers.json")
    assert openers["frequency"]["first"] == make_agent("frequency").choose_guess([], answers)
    entropy = make_agent("entropy", table=table)
    first = entropy.choose_guess([], answers)
    assert openers["entropy"]["first"] == first
    second = openers["entropy"]["second"]
    assert sorted(map(int, second)) == sorted({feedback(first, w) for w in answers})
    for pattern, entry in list(second.items())[::7]:
        candidates = [w for w in answers if feedback(first, w) == int(pattern)]
        assert entry["candidates"] == len(candidates)
        assert entropy.choose_guess([(first, int(pattern))], candidates) == entry["guess"]


def test_feedback_fixtures_match_python():
    fixtures = load("feedback_fixtures.json")
    assert len(fixtures["triples"]) >= 2000
    for guess, answer, pattern in fixtures["triples"]:
        assert feedback(guess, answer) == pattern
    for case in fixtures["cases"]:
        assert feedback(case["guess"], case["answer"]) == case["pattern"]
        assert pattern_to_emoji(case["pattern"]) == case["emoji"]
    for item in fixtures["describe"]:
        history = [(g, p) for g, p in item["history"]]
        assert Constraints.from_history(history).describe() == item["text"]
    assert len(fixtures["contradictions"]) == 5


def test_agent_games_are_real_games(answers):
    fixtures = load("agent_fixtures.json")
    answer_set = set(answers)
    for name, games in fixtures["games"].items():
        assert len(games) == len(fixtures["words"])
        for word, guesses in zip(fixtures["words"], games):
            assert word in answer_set and guesses[-1] == word


def test_summary_matches_the_results():
    summary = load("summary.json")
    comparison = json.loads((RESULTS_DIR / "comparison.json").read_text(encoding="utf-8"))
    assert [a["name"] for a in summary["agents"]] == list(comparison["agents"])
    for agent in summary["agents"]:
        assert agent["mean"] == round(comparison["agents"][agent["name"]]["mean"], 4)
    assert summary["answers"] == 1900 and summary["guesses"] == 5370
