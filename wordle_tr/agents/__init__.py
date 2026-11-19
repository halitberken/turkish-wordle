"""Agent registry: ``make_agent(name, seed, table)`` builds any registered agent."""

from __future__ import annotations

import functools
from collections.abc import Callable

from wordle_tr.agents.base import Agent
from wordle_tr.agents.baselines import LetterFrequencyAgent, RandomAgent
from wordle_tr.agents.entropy import EntropyAgent, frequency_prior
from wordle_tr.agents.expectimax import ExpectimaxAgent
from wordle_tr.pattern_table import PatternTable
from wordle_tr.words import load_frequencies


@functools.lru_cache(maxsize=1)
def default_table() -> PatternTable:
    """The pattern table of the default word lists (loaded from the cache once per process)."""
    return PatternTable.load_or_build()


def _entropy_freq(table: PatternTable) -> EntropyAgent:
    prior = frequency_prior(table.answers, load_frequencies())
    return EntropyAgent(table, prior=prior, name="entropy_freq")


def _expectimax(table: PatternTable, depth: int | None, width: int | None) -> ExpectimaxAgent:
    return ExpectimaxAgent(table, depth=depth or DEFAULT_DEPTH, width=width or DEFAULT_WIDTH)


Factory = Callable[..., Agent]
DEFAULT_DEPTH, DEFAULT_WIDTH = 2, 10

AGENTS: dict[str, Factory] = {
    "random": lambda seed, table, **_: RandomAgent(seed),
    "frequency": lambda seed, table, **_: LetterFrequencyAgent(),
    "entropy": lambda seed, table, **_: EntropyAgent(table, name="entropy"),
    "entropy_candidates": lambda seed, table, **_: EntropyAgent(table, candidates_only=True,
                                                                name="entropy_candidates"),
    "entropy_freq": lambda seed, table, **_: _entropy_freq(table),
    "most_parts": lambda seed, table, **_: EntropyAgent(table, score="parts", name="most_parts"),
    "expectimax": lambda seed, table, depth=None, width=None, **_: _expectimax(table, depth, width),
}
NEEDS_TABLE = {"entropy", "entropy_candidates", "entropy_freq", "most_parts", "expectimax"}


def make_agent(name: str, seed: int = 0, table: PatternTable | None = None, **options: int | None) -> Agent:
    """Build the agent registered as ``name``.

    ``seed`` is used by random agents; ``table`` by the agents that search with the pattern
    table (default: the cached table of the default word lists); ``options`` (``depth``,
    ``width``) by the expectimax agent.
    """
    try:
        factory = AGENTS[name]
    except KeyError:
        raise ValueError(f"unknown agent {name!r}; choose from {', '.join(AGENTS)}") from None
    if table is None and name in NEEDS_TABLE:
        table = default_table()
    return factory(seed, table, **options)


__all__ = ["AGENTS", "Agent", "EntropyAgent", "ExpectimaxAgent", "LetterFrequencyAgent", "RandomAgent",
           "default_table", "make_agent"]
