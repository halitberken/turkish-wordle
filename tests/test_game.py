"""Week 7: the game environment and the terminal script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from wordle_tr.feedback import ALL_GREEN, parse_pattern
from wordle_tr.game import InvalidGuessError, WordleGame

PLAY = Path(__file__).resolve().parent.parent / "scripts" / "play.py"


def test_win_in_two(guesses):
    game = WordleGame("kalem", guesses)
    assert game.play("kapak") == parse_pattern("ggxxx")
    assert not game.over
    assert game.play("kalem") == ALL_GREEN
    assert game.won and game.over and game.guesses_used == 2
    assert game.history == [("kapak", parse_pattern("ggxxx")), ("kalem", ALL_GREEN)]


def test_game_ends_after_six(guesses):
    game = WordleGame("kalem", guesses)
    for word in ["erika", "üzgün", "kapak", "ekler", "tatlı", "kayak"]:
        game.play(word)
    assert game.over and not game.won and game.guesses_used == 6
    with pytest.raises(InvalidGuessError):
        game.play("kalem")
    assert game.guesses_used == 6


@pytest.mark.parametrize("bad", ["kale", "kalemi", "zzzzz", "quest", "kal m", ""])
def test_invalid_guesses_do_not_use_a_turn(guesses, bad):
    game = WordleGame("kalem", guesses)
    game.play("erika")
    with pytest.raises(InvalidGuessError):
        game.play(bad)
    assert game.guesses_used == 1 and not game.over


def test_no_guess_after_a_win(guesses):
    game = WordleGame("kalem", guesses)
    game.play("kalem")
    with pytest.raises(InvalidGuessError):
        game.play("erika")


def test_guesses_are_normalised_with_turkish_case_rules(guesses):
    game = WordleGame("erika", guesses)
    assert game.play("ERİKA") == ALL_GREEN
    game = WordleGame("kılıç", guesses)
    assert game.play(" KILIÇ ") == ALL_GREEN  # I -> ı, not i


def test_without_a_word_list_any_turkish_word_is_accepted():
    game = WordleGame("kalem")
    game.play("zzzzz")
    assert game.guesses_used == 1


def test_unlimited_mode(guesses):
    game = WordleGame("kalem", guesses, max_guesses=None)
    for word in ["erika", "üzgün", "kapak", "ekler", "tatlı", "kayak", "sayma", "yazma"]:
        game.play(word)
    assert not game.over and game.guesses_used == 8
    assert game.play("kalem") == ALL_GREEN and game.won and game.guesses_used == 9


def test_bad_setup_is_rejected(guesses):
    with pytest.raises(ValueError):
        WordleGame("kale")
    with pytest.raises(ValueError):
        WordleGame("zzzzz", guesses)
    with pytest.raises(ValueError):
        WordleGame("kalem", guesses, max_guesses=0)


def run_play(*args: str, stdin: str = "") -> str:
    result = subprocess.run([sys.executable, str(PLAY), *args], input=stdin, capture_output=True,
                            text=True, encoding="utf-8", timeout=60, check=True)
    return result.stdout


def test_script_watch():
    out = run_play("watch", "--agent", "frequency", "--word", "sayma", "--no-color")
    assert "1. ERİKA  ⬜⬜⬜⬜🟩" in out
    assert "Solved in 8 guesses." in out


def test_script_play():
    out = run_play("play", "--word", "kalem", "--no-color", stdin="kale\nkapak\nkalem\n")
    assert "not 5 Turkish letters" in out
    assert "Solved in 2/6!" in out and "🟩🟩⬜⬜⬜" in out


def test_script_assist_detects_contradictions():
    out = run_play("assist", "--no-color", stdin="\nxxxxg\n\nxxxgg\nkalem\nggggg\nsaçma\nggxgg\nquit\n")
    assert "Suggestion: ERİKA" in out
    assert "Known: Letter 4 is M; letter 5 is A" in out
    assert "Contradictory input" in out
    assert "Candidates:" in out
