"""Shared fixtures. Tests marked ``slow`` are skipped unless ``--runslow`` is given."""

from __future__ import annotations

import pytest

from wordle_tr.csp_solver import CSPSolver
from wordle_tr.pattern_table import PatternTable
from wordle_tr.simulate import random_histories as random_histories_for
from wordle_tr.words import load_answers, load_guesses


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--runslow", action="store_true", default=False, help="also run slow tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="slow; use --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="session")
def guesses() -> list[str]:
    return load_guesses()


@pytest.fixture(scope="session")
def answers() -> list[str]:
    return load_answers()


@pytest.fixture(scope="session")
def random_histories(answers, guesses) -> list[tuple[str, list[tuple[str, int]]]]:
    """300 game states (seed 1234): a hidden answer and 1-4 random guesses with their patterns."""
    return random_histories_for(answers, guesses, n=300, seed=1234)


@pytest.fixture(scope="session")
def table(guesses, answers) -> PatternTable:
    return PatternTable.load_or_build(guesses, answers)


@pytest.fixture(scope="session")
def solver(answers) -> CSPSolver:
    return CSPSolver(answers)
