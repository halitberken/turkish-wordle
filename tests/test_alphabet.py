"""Week 6: Turkish alphabet, case conversion, normalisation, sorting and the word lists."""

from __future__ import annotations

import numpy as np
import pytest

from wordle_tr.alphabet import (
    ALPHABET,
    UPPER_ALPHABET,
    is_valid_word,
    normalize,
    sort_key,
    to_lower,
    to_upper,
    turkish_sorted,
)
from wordle_tr.stats import letter_presence, one_letter_families, opener_scores, repeated_letter_share
from wordle_tr.words import (
    ANSWERS_PATH,
    EXCLUDED_PATH,
    FREQUENCIES_PATH,
    GUESSES_PATH,
    build_word_lists,
    encode,
    load_frequencies,
    read_word_file,
)


def test_alphabet_has_29_distinct_letters():
    assert len(ALPHABET) == 29
    assert len(set(ALPHABET)) == 29
    assert not set("qwx") & set(ALPHABET)
    assert [to_upper(c) for c in ALPHABET] == list(UPPER_ALPHABET)


def test_to_lower_handles_dotted_and_dotless_i():
    assert "İ".lower() != "i"  # the pitfall: Python adds a combining dot
    assert to_lower("İSTANBUL") == "istanbul"
    assert to_lower("IŞIK") == "ışık"
    assert to_lower("ÇĞÖŞÜ") == "çğöşü"
    assert to_lower("İ") == "i"  # decomposed İ


def test_to_upper_handles_dotted_and_dotless_i():
    assert "i".upper() == "I"  # the pitfall: should be İ
    assert to_upper("ılık") == "ILIK"
    assert to_upper("istanbul") == "İSTANBUL"
    assert all(to_lower(to_upper(c)) == c for c in ALPHABET)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  Kâğıt ", "kağıt"),
        ("hâlâ", "hala"),
        ("\tÎmân\n", "iman"),
        ("Ûslup", "uslup"),
        ("âdet", "adet"),  # decomposed circumflex
        ("kalem", "kalem"),
    ],
)
def test_normalize_removes_circumflexes_and_whitespace(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize("word", ["kalem", "ışığı", "çiçek", "üzgün", "abcçd"])
def test_is_valid_word_accepts(word):
    assert is_valid_word(word)


@pytest.mark.parametrize("word", ["kale", "kalemi", "Kalem", "KALEM", "kâlem", "quest", "kal m", ""])
def test_is_valid_word_rejects(word):
    assert not is_valid_word(word)


def test_sort_key_follows_turkish_order():
    assert sorted(["i", "ı", "d", "ç", "c"], key=sort_key) == ["c", "ç", "d", "ı", "i"]
    assert turkish_sorted(["dal", "çay", "cam"]) == ["cam", "çay", "dal"]
    assert turkish_sorted(["iğne", "ılık"]) == ["ılık", "iğne"]
    assert turkish_sorted(["ütü", "uzun", "öykü", "oyun", "şal", "sal", "ğ", "g"]) == [
        "g", "ğ", "oyun", "öykü", "sal", "şal", "uzun", "ütü"]


def test_encode():
    codes = encode(["abcçd", "zzzzz"])
    assert codes.dtype == np.uint8 and codes.shape == (2, 5)
    assert codes[0].tolist() == [0, 1, 2, 3, 4]
    assert codes[1].tolist() == [28] * 5
    with pytest.raises(ValueError):
        encode(["kale"])


def test_word_lists_are_clean(guesses, answers):
    for words in (guesses, answers):
        assert all(is_valid_word(w) for w in words)
        assert all(w == to_lower(w) for w in words)
        assert len(set(words)) == len(words)
        assert words == turkish_sorted(words)
    assert set(answers) <= set(guesses)
    excluded = set(read_word_file(EXCLUDED_PATH))
    assert excluded <= set(guesses)
    assert not excluded & set(answers)


def test_output_files_have_a_one_line_header():
    for path in (GUESSES_PATH, ANSWERS_PATH, FREQUENCIES_PATH):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# ")
        assert not any(line.startswith("#") for line in lines[1:])


def test_frequencies_cover_exactly_the_answers(answers):
    frequencies = load_frequencies()
    assert list(frequencies) == answers
    assert all(count > 0 for count in frequencies.values())


def test_committed_lists_are_reproducible_from_raw(guesses, answers):
    build = build_word_lists()
    assert build.guesses == guesses
    assert build.answers == answers
    assert build.frequencies == load_frequencies()


def test_statistics_on_a_tiny_list():
    words = ["saçma", "sanma", "kalem", "kayak"]
    presence = letter_presence(words)
    assert presence["a"] == 100.0 and presence["k"] == 50.0 and presence["z"] == 0.0
    assert repeated_letter_share(words) == 75.0  # saçma, sanma, kayak
    assert one_letter_families(words) == [("sa_ma", ["saçma", "sanma"])]
    top = opener_scores(["kayak", "kalem"], words, top=2)
    assert [r["word"] for r in top] == ["kalem", "kayak"]
    assert top[0]["answers_sharing_a_letter_pct"] == 100.0
