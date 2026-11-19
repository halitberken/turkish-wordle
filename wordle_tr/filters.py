"""Candidate-filtering methods behind one interface: ``filter_fn(candidates, guess, pattern)``.

The game loop owns filtering, so any method here can be swapped in without
touching the agents. All methods return the same candidates in the same order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from wordle_tr.constraints import Constraints
from wordle_tr.feedback import filter_candidates

FilterFn = Callable[[list[str], str, int], list[str]]


def filter_by_constraints(candidates: Iterable[str], guess: str, pattern: int) -> list[str]:
    """Keep the words that satisfy the constraints of one observation."""
    constraints = Constraints.from_history([(guess, pattern)])
    return [w for w in candidates if constraints.is_satisfied(w)]


FILTERS: dict[str, FilterFn] = {
    "feedback": filter_candidates,  # reference: recompute feedback for every candidate
    "constraints": filter_by_constraints,
}


def make_filter(name: str) -> FilterFn:
    try:
        return FILTERS[name]
    except KeyError:
        raise ValueError(f"unknown filter {name!r}; choose from {', '.join(FILTERS)}") from None
