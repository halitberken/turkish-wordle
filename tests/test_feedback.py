"""Week 7: feedback rule, pattern encoding and the reference filter."""

from __future__ import annotations

import itertools
import random
from collections import Counter

import pytest

from wordle_tr.alphabet import normalize
from wordle_tr.feedback import (
    ALL_GREEN,
    GREEN,
    GREY,
    NUM_PATTERNS,
    YELLOW,
    decode_pattern,
    encode_colors,
    feedback,
    filter_candidates,
    is_consistent,
    letter_states,
    parse_pattern,
    pattern_to_emoji,
    pattern_to_text,
)


@pytest.mark.parametrize(
    "guess, answer, emoji",
    [
        ("KAPAK", "KALEM", "🟩🟩⬜⬜⬜"),
        ("EKLER", "KALEM", "⬜🟨🟩🟩⬜"),
        ("TATLI", "OTLAK", "🟨🟨⬜🟨⬜"),
        ("KEKİK", "KAYAK", "🟩⬜⬜⬜🟩"),
        ("KALEM", "KALEM", "🟩🟩🟩🟩🟩"),
        ("ÜZGÜN", "KALEM", "⬜⬜⬜⬜⬜"),
        ("AAAAA", "KAPAK", "⬜🟩⬜🟩⬜"),  # extra copies are grey once all are accounted for
        ("ALAKA", "KAPAK", "🟨⬜🟨🟨⬜"),  # two A's in the answer: only the first two non-green A's are yellow
        ("SAYMA", "SAÇMA", "🟩🟩⬜🟩🟩"),
    ],
)
def test_duplicate_letter_cases(guess, answer, emoji):
    pattern = feedback(normalize(guess), normalize(answer))
    assert pattern_to_emoji(pattern) == emoji


def test_all_green_and_all_grey():
    assert feedback("kalem", "kalem") == ALL_GREEN == 242
    assert feedback("üzgün", "kalem") == 0


def test_encoding_convention():
    # position 0 is the most significant base-3 digit; grey 0, yellow 1, green 2
    assert encode_colors([GREEN, GREEN, GREY, GREY, GREY]) == 2 * 81 + 2 * 27
    assert encode_colors([GREY, GREY, GREY, GREY, YELLOW]) == 1
    assert NUM_PATTERNS == 243


def test_encoding_round_trip_for_all_243_patterns():
    for pattern in range(NUM_PATTERNS):
        assert encode_colors(decode_pattern(pattern)) == pattern
    for colors in itertools.product((GREY, YELLOW, GREEN), repeat=5):
        assert decode_pattern(encode_colors(colors)) == list(colors)
    with pytest.raises(ValueError):
        decode_pattern(243)
    with pytest.raises(ValueError):
        encode_colors([3, 0, 0, 0, 0])


@pytest.mark.parametrize("text", ["ggy..", "ggyxx", "GGYXX", " g g y x x ", "🟩🟩🟨⬜⬜", "🟩🟩🟨⬛⬛", "🟩🟩🟨⬜️⬜️"])
def test_parse_pattern(text):
    assert parse_pattern(text) == encode_colors([GREEN, GREEN, YELLOW, GREY, GREY])


@pytest.mark.parametrize("text", ["ggyx", "ggyxxx", "ggyxz", "", "22100"])
def test_parse_pattern_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_pattern(text)


def test_text_and_emoji_round_trip():
    for pattern in range(NUM_PATTERNS):
        assert parse_pattern(pattern_to_text(pattern)) == pattern
        assert parse_pattern(pattern_to_emoji(pattern)) == pattern


def test_green_plus_yellow_count_is_min_of_letter_counts(guesses, answers):
    """Key lemma of the week 8 proof, checked on random pairs."""
    rng = random.Random(7)
    for _ in range(5000):
        g, a = rng.choice(guesses), rng.choice(answers)
        colors = decode_pattern(feedback(g, a))
        found = Counter(letter for letter, c in zip(g, colors) if c != GREY)
        ng, na = Counter(g), Counter(a)
        assert all(found[letter] == min(ng[letter], na[letter]) for letter in ng)
        assert all((c == GREEN) == (x == y) for x, y, c in zip(g, a, colors))


def test_filter_always_keeps_the_answer(random_histories, answers):
    for answer, history in random_histories:
        candidates = answers
        for guess, pattern in history:
            candidates = filter_candidates(candidates, guess, pattern)
        assert answer in candidates
        assert all(is_consistent(w, history) for w in candidates)


def test_filter_matches_brute_force(random_histories, answers):
    for _, history in random_histories[:50]:
        candidates = answers
        for guess, pattern in history:
            candidates = filter_candidates(candidates, guess, pattern)
        assert candidates == [w for w in answers if is_consistent(w, history)]


def test_letter_states_keep_the_best_colour():
    history = [("kapak", feedback("kapak", "kalem")), ("ekler", feedback("ekler", "kalem"))]
    states = letter_states(history)
    assert states["k"] == GREEN and states["a"] == GREEN and states["l"] == GREEN
    assert states["p"] == GREY and states["r"] == GREY and states["e"] == GREEN
