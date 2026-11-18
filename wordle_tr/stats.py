"""Descriptive statistics of the word lists (week 6)."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from wordle_tr.alphabet import ALPHABET, LETTER_INDEX, sort_key, turkish_sorted

TURKISH_SPECIFIC = "çğıöşü"  # letters that are not in the English alphabet


def letter_presence(words: list[str]) -> dict[str, float]:
    """Percentage of ``words`` that contain each letter at least once (alphabet order)."""
    return {
        letter: 100.0 * sum(letter in word for word in words) / len(words)
        for letter in ALPHABET
    }


def repeated_letter_share(words: list[str]) -> float:
    """Percentage of ``words`` with at least one repeated letter."""
    return 100.0 * sum(len(set(word)) < len(word) for word in words) / len(words)


def _letter_masks(words: list[str]) -> np.ndarray:
    return np.array([sum(1 << LETTER_INDEX[c] for c in set(word)) for word in words], dtype=np.int64)


def opener_scores(openers: list[str], answers: list[str], top: int = 10) -> list[dict]:
    """Rank openers by distinct-letter coverage of the answer list.

    ``expected_letters_hit`` = sum over the opener's distinct letters of the
    fraction of answers containing that letter, i.e. the expected number of the
    opener's letters that turn green or yellow. Ties go to Turkish order.
    """
    presence = letter_presence(answers)
    hit_masks = _letter_masks(openers)[:, None] & _letter_masks(answers)[None, :]
    sharing = 100.0 * (hit_masks != 0).mean(axis=1)
    rows = [
        {
            "word": word,
            "expected_letters_hit": sum(presence[c] for c in set(word)) / 100.0,
            "answers_sharing_a_letter_pct": float(share),
        }
        for word, share in zip(openers, sharing)
    ]
    rows.sort(key=lambda r: (-round(r["expected_letters_hit"], 12), sort_key(r["word"])))
    return rows[:top]


def one_letter_families(words: list[str]) -> list[tuple[str, list[str]]]:
    """Groups of 2+ words that differ only at one position, largest first.

    The family pattern marks the free position with ``_`` (e.g. ``sa_ma``).
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for word in words:
        for i in range(len(word)):
            groups[word[:i] + "_" + word[i + 1:]].append(word)
    families = [(pattern, turkish_sorted(members)) for pattern, members in groups.items()
                if len(members) >= 2]
    families.sort(key=lambda f: (-len(f[1]), sort_key(f[0])))
    return families


def word_statistics(answers: list[str], guesses: list[str], top: int = 10) -> dict:
    """All week-6 statistics as a JSON-ready dict (percentages rounded to 2 decimals)."""
    presence = letter_presence(answers)
    families = one_letter_families(answers)
    in_family = {word for _, members in families for word in members}
    size_counts: dict[int, int] = defaultdict(int)
    for _, members in families:
        size_counts[len(members)] += 1

    def has_turkish(word: str) -> bool:
        return any(c in TURKISH_SPECIFIC for c in word)

    def pct(value: float) -> float:
        return round(value, 2)

    def rounded(rows: list[dict]) -> list[dict]:
        return [{"word": r["word"],
                 "expected_letters_hit": round(r["expected_letters_hit"], 4),
                 "answers_sharing_a_letter_pct": pct(r["answers_sharing_a_letter_pct"])}
                for r in rows]

    return {
        "answers": len(answers),
        "guesses": len(guesses),
        "letter_presence_pct": {c: pct(v) for c, v in presence.items()},
        "letters_by_presence": [[c, pct(presence[c])]
                                for c in sorted(ALPHABET, key=lambda c: (-presence[c], sort_key(c)))],
        "turkish_specific_letters": TURKISH_SPECIFIC,
        "answers_with_turkish_specific_letter_pct": pct(
            100.0 * sum(map(has_turkish, answers)) / len(answers)),
        "guesses_with_turkish_specific_letter_pct": pct(
            100.0 * sum(map(has_turkish, guesses)) / len(guesses)),
        "answers_with_repeated_letter_pct": pct(repeated_letter_share(answers)),
        "guesses_with_repeated_letter_pct": pct(repeated_letter_share(guesses)),
        "best_openers_all_guesses": rounded(opener_scores(guesses, answers, top)),
        "best_openers_answers_only": rounded(opener_scores(answers, answers, top)),
        "one_letter_families": {
            "answers_with_a_one_letter_neighbour": len(in_family),
            "answers_with_a_one_letter_neighbour_pct": pct(100.0 * len(in_family) / len(answers)),
            "families_by_size": {str(k): size_counts[k] for k in sorted(size_counts)},
            "largest": [{"pattern": p, "size": len(m), "words": m} for p, m in families[:top]],
        },
    }
