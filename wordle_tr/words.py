"""Word lists: loading, letter encoding and the build pipeline from raw sources."""

from __future__ import annotations

import hashlib
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from wordle_tr import DATA_DIR
from wordle_tr.alphabet import LETTER_INDEX, WORD_LENGTH, is_valid_word, normalize, turkish_sorted

RAW_DIR = DATA_DIR / "raw"
GUESSES_PATH = DATA_DIR / "guesses.txt"
ANSWERS_PATH = DATA_DIR / "answers.txt"
FREQUENCIES_PATH = DATA_DIR / "frequencies.tsv"
EXCLUDED_PATH = DATA_DIR / "excluded_answers.txt"
DICTIONARY_PATHS = (RAW_DIR / "tdk_cannuhlar.txt", RAW_DIR / "tdk_mertemin.txt")
SUBTITLE_PATH = RAW_DIR / "opensubtitles_tr_50k.txt"

_CIRCUMFLEXES = set("âîûÂÎÛ")


# --------------------------------------------------------------------------- loading


def read_word_file(path: Path) -> list[str]:
    """Read one word per line, skipping blank lines and ``#`` comment lines."""
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(normalize(line))
    return words


def load_guesses(path: Path | None = None) -> list[str]:
    """All valid guesses (Turkish alphabetical order)."""
    return read_word_file(path or GUESSES_PATH)


def load_answers(path: Path | None = None) -> list[str]:
    """Possible hidden words (Turkish alphabetical order), a subset of the guesses."""
    return read_word_file(path or ANSWERS_PATH)


def load_frequencies(path: Path | None = None) -> dict[str, int]:
    """Subtitle occurrence count of every answer word."""
    frequencies = {}
    for line in Path(path or FREQUENCIES_PATH).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            word, count = line.split("\t")
            frequencies[word] = int(count)
    return frequencies


def encode(words: list[str]) -> np.ndarray:
    """Encode words as a ``(len(words), 5)`` uint8 array of letter codes 0..28."""
    codes = np.zeros((len(words), WORD_LENGTH), dtype=np.uint8)
    for i, word in enumerate(words):
        if not is_valid_word(word):
            raise ValueError(f"not a valid {WORD_LENGTH}-letter Turkish word: {word!r}")
        codes[i] = [LETTER_INDEX[letter] for letter in word]
    return codes


# --------------------------------------------------------------------------- building


@dataclass
class WordListBuild:
    """Result of :func:`build_word_lists`, with the counts after every step."""

    guesses: list[str]
    answers: list[str]
    frequencies: dict[str, int]
    excluded: list[str]
    steps: list[tuple[str, int]] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)


def read_raw_entries(path: Path) -> list[str]:
    """Non-empty lines of a raw dictionary file, NFC-normalised and stripped.

    Splits on ``\\n`` only: a few entries contain U+0085 (e.g. ``ha \\x85 ha``),
    which ``str.splitlines`` would treat as a line break.
    """
    text = unicodedata.normalize("NFC", Path(path).read_text(encoding="utf-8"))
    return [line.strip() for line in text.split("\n") if line.strip()]


def read_subtitle_tokens(path: Path) -> list[tuple[str, int]]:
    """``(token, count)`` pairs of the subtitle frequency list, in file order."""
    pairs = []
    for line in Path(path).read_text(encoding="utf-8").split("\n"):
        if line.strip():
            token, count = line.rsplit(" ", 1)
            pairs.append((token, int(count)))
    return pairs


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_word_lists(
    dictionary_paths: tuple[Path, ...] = DICTIONARY_PATHS,
    subtitle_path: Path = SUBTITLE_PATH,
    excluded_path: Path = EXCLUDED_PATH,
) -> WordListBuild:
    """Build the guess list, the answer list and answer frequencies (section 4)."""
    steps: list[tuple[str, int]] = []
    sources = {}
    entries: list[str] = []
    for path in dictionary_paths:
        file_entries = read_raw_entries(path)
        sources[Path(path).name] = {"entries": len(file_entries), "sha256": sha256(path)}
        entries += file_entries
    steps.append(("raw dictionary entries (both lists)", len(entries)))

    entries = [e for e in entries if not e[0].isupper()]
    steps.append(("after dropping proper nouns (upper-case first letter)", len(entries)))

    entries = [e for e in entries if all(c.isalpha() for c in e)]
    steps.append(("after dropping multi-word / punctuated entries", len(entries)))

    five = [(e, normalize(e)) for e in entries if is_valid_word(normalize(e))]
    steps.append(("exactly 5 Turkish letters after normalisation", len(five)))

    guesses = turkish_sorted({word for _, word in five})
    steps.append(("deduplicated -> guess list", len(guesses)))

    tokens = read_subtitle_tokens(subtitle_path)
    sources[Path(subtitle_path).name] = {"entries": len(tokens), "sha256": sha256(subtitle_path)}
    # The source was lower-cased without Turkish rules (it has both "İyi" and "iyi"),
    # so tokens are normalised too and the counts of merged spellings add up.
    subtitle_counts: Counter[str] = Counter()
    spellings: dict[str, set[str]] = defaultdict(set)
    for token, count in tokens:
        subtitle_counts[normalize(token)] += count
        spellings[normalize(token)].add(token)
    common = [w for w in guesses if w in subtitle_counts]
    steps.append(("also in the 50k subtitle list -> common words", len(common)))

    excluded = set(read_word_file(excluded_path))
    unknown = turkish_sorted(excluded - set(common))
    if unknown:
        raise ValueError(f"excluded words that are not common words (typo?): {unknown}")
    answers = [w for w in common if w not in excluded]
    steps.append(("after removing excluded (offensive) words -> answer list", len(answers)))

    with_circumflex = {word for entry, word in five if _CIRCUMFLEXES & set(entry)}
    without_circumflex = {word for entry, word in five if not _CIRCUMFLEXES & set(entry)}
    merged_spellings = [w for w in answers if len(spellings[w]) > 1]
    raw_token_set = {token for token, _ in tokens}
    details = {
        "sources": sources,
        "circumflex_words": len(with_circumflex),
        "circumflex_words_merged_with_plain_spelling": len(with_circumflex & without_circumflex),
        "circumflex_examples": [e for e, _ in five if _CIRCUMFLEXES & set(e)][:8],
        "circumflex_merged_examples": turkish_sorted(with_circumflex & without_circumflex)[:8],
        "answers_with_merged_subtitle_spellings": len(merged_spellings),
        "merged_subtitle_spelling_examples": {
            w: sorted(spellings[w]) for w in merged_spellings[:8]},
        "common_words_missed_without_turkish_normalisation": len(
            [w for w in common if w not in raw_token_set]),
        "excluded_words": turkish_sorted(excluded),
    }
    return WordListBuild(
        guesses=guesses,
        answers=answers,
        frequencies={w: subtitle_counts[w] for w in answers},
        excluded=turkish_sorted(excluded),
        steps=steps,
        details=details,
    )


def write_word_file(path: Path, words: list[str], header: str) -> None:
    """Write a one-line ``#`` header followed by one word per line."""
    Path(path).write_text(f"# {header}\n" + "".join(f"{w}\n" for w in words), encoding="utf-8")


def write_frequencies(path: Path, frequencies: dict[str, int], header: str) -> None:
    """Write ``word<TAB>count`` lines in Turkish alphabetical order."""
    lines = [f"{w}\t{frequencies[w]}\n" for w in turkish_sorted(set(frequencies))]
    Path(path).write_text(f"# {header}\n" + "".join(lines), encoding="utf-8")
