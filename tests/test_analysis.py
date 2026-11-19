"""Week 11: the statistics used to compare agents."""

from __future__ import annotations

import numpy as np
import pytest

from wordle_tr.analysis import (
    bootstrap_ci,
    bootstrap_indices,
    family_bucket,
    paired_comparison,
    sign_flip_p_value,
    solved_by_turn,
)


def test_bootstrap_is_seeded_and_covers_the_mean():
    values = np.random.default_rng(0).integers(2, 7, size=500).astype(float)
    a, b = bootstrap_indices(500, 2000, seed=1), bootstrap_indices(500, 2000, seed=1)
    assert np.array_equal(a, b)
    low, high = bootstrap_ci(values, a)
    assert low < values.mean() < high
    assert high - low < 0.3


def test_constant_values_give_a_zero_width_interval():
    values = np.full(100, 3.0)
    assert bootstrap_ci(values, bootstrap_indices(100, 500, seed=2)) == (3.0, 3.0)


def test_paired_comparison_counts_and_significance():
    rng = np.random.default_rng(3)
    a = rng.integers(3, 6, size=400).astype(float)
    b = a - (rng.random(400) < 0.3)  # b is better on about 30 % of the words
    result = paired_comparison(a, b, bootstrap_indices(400, 2000, seed=4), permutations=2000, seed=5)
    assert result["b_better"] + result["b_worse"] + result["equal"] == 400
    assert result["b_worse"] == 0 and result["mean_difference"] > 0
    assert result["ci_low"] > 0 and result["p_value"] < 0.01


def test_no_difference_is_not_significant():
    rng = np.random.default_rng(6)
    d = rng.choice([-1.0, 0.0, 1.0], size=600)
    assert sign_flip_p_value(d - d.mean(), 2000, seed=7) > 0.5
    assert sign_flip_p_value(np.zeros(50), 1000, seed=8) == 1.0


def test_solved_by_turn_and_buckets():
    assert solved_by_turn([1, 2, 2, 3, 5], 5) == pytest.approx([20.0, 60.0, 80.0, 80.0, 100.0])
    assert [family_bucket(s) for s in (1, 2, 3, 4, 5, 8)] == [
        "no neighbour", "family of 2", "family of 3-4", "family of 3-4", "family of 5+", "family of 5+"]
