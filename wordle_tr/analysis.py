"""Statistics for comparing agents (week 11): bootstrap intervals, paired tests, difficulty buckets.

All randomness is seeded. Every agent is evaluated on the same 1,900 hidden
words, so comparisons are *paired*: for each word w the difference
d_w = guesses_A(w) - guesses_B(w) is formed, and its mean is examined.

* Bootstrap: resample the words with replacement (the same resamples for every
  agent and pair) and take the 2.5 % and 97.5 % percentiles of the mean.
* Sign-flip permutation test: under "no difference", each d_w is equally likely
  to have either sign; the p-value is the share of random sign flips whose mean
  is at least as far from 0 as the observed mean.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

CHUNK = 1000  # resamples handled at once, to bound memory


def bootstrap_indices(n: int, resamples: int, seed: int) -> np.ndarray:
    """``resamples`` rows of ``n`` word indices drawn with replacement."""
    dtype = np.uint16 if n < 2**16 else np.int64
    return np.random.default_rng(seed).integers(0, n, size=(resamples, n)).astype(dtype)


def bootstrap_means(values: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """The mean of ``values`` in every bootstrap resample."""
    values = np.asarray(values, dtype=float)
    means = np.empty(len(indices))
    for start in range(0, len(indices), CHUNK):
        means[start:start + CHUNK] = values[indices[start:start + CHUNK]].mean(axis=1)
    return means


def bootstrap_ci(values: np.ndarray, indices: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    """Percentile confidence interval for the mean of ``values``."""
    tail = 100 * (1 - level) / 2
    low, high = np.percentile(bootstrap_means(values, indices), [tail, 100 - tail])
    return float(low), float(high)


def sign_flip_p_value(differences: np.ndarray, permutations: int, seed: int) -> float:
    """Two-sided p-value of a paired sign-flip permutation test for mean(differences) = 0."""
    d = np.asarray(differences, dtype=float)
    observed = abs(d.mean())
    rng = np.random.default_rng(seed)
    hits = 0
    for start in range(0, permutations, CHUNK):
        size = min(CHUNK, permutations - start)
        signs = rng.integers(0, 2, size=(size, len(d)), dtype=np.int8) * 2 - 1
        hits += int((np.abs((signs * d).mean(axis=1)) >= observed - 1e-12).sum())
    return (hits + 1) / (permutations + 1)


def paired_comparison(a: np.ndarray, b: np.ndarray, indices: np.ndarray, permutations: int,
                      seed: int) -> dict:
    """Compare two agents on the same words: positive differences mean ``b`` needs fewer guesses."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    low, high = bootstrap_ci(d, indices)
    return {
        "mean_difference": float(d.mean()),
        "ci_low": low,
        "ci_high": high,
        "b_better": int((d > 0).sum()),
        "b_worse": int((d < 0).sum()),
        "equal": int((d == 0).sum()),
        "p_value": sign_flip_p_value(d, permutations, seed),
    }


def solved_by_turn(guesses: Sequence[float], max_turn: int) -> list[float]:
    """Percentage of words solved within t guesses, for t = 1..max_turn."""
    g = np.asarray(guesses, dtype=float)
    return [float(100.0 * (g <= t).mean()) for t in range(1, max_turn + 1)]


def family_bucket(size: int) -> str:
    """Difficulty bucket of a word by the size of its largest one-letter family."""
    if size <= 1:
        return "no neighbour"
    if size == 2:
        return "family of 2"
    if size <= 4:
        return "family of 3-4"
    return "family of 5+"


BUCKETS = ["no neighbour", "family of 2", "family of 3-4", "family of 5+"]
