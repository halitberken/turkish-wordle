"""Shared fixtures. Tests marked ``slow`` are skipped unless ``--runslow`` is given."""

from __future__ import annotations

import pytest

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
