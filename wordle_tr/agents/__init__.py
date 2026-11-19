"""Agent registry: ``make_agent(name, seed, table)`` builds any registered agent."""

from __future__ import annotations

import functools
from collections.abc import Callable

from wordle_tr.agents.base import Agent
from wordle_tr.agents.baselines import LetterFrequencyAgent, RandomAgent
from wordle_tr.agents.entropy import EntropyAgent, frequency_prior
from wordle_tr.pattern_table import PatternTable
from wordle_tr.words import load_frequencies


@functools.lru_cache(maxsize=1)
def default_table() -> PatternTable:
    """The pattern table of the default word lists (loaded from the cache once per process)."""
    return PatternTable.load_or_build()


def _entropy_freq(table: PatternTable) -> EntropyAgent:
    prior = frequency_prior(table.answers, load_frequencies())
    return EntropyAgent(table, prior=prior, name="entropy_freq")


Factory = Callable[[int, PatternTable], Agent]

AGENTS: dict[str, Factory] = {
    "random": lambda seed, table: RandomAgent(seed),
    "frequency": lambda seed, table: LetterFrequencyAgent(),
    "entropy": lambda seed, table: EntropyAgent(table, name="entropy"),
    "entropy_candidates": lambda seed, table: EntropyAgent(table, candidates_only=True,
                                                           name="entropy_candidates"),
    "entropy_freq": lambda seed, table: _entropy_freq(table),
    "most_parts": lambda seed, table: EntropyAgent(table, score="parts", name="most_parts"),
}
NEEDS_TABLE = {"entropy", "entropy_candidates", "entropy_freq", "most_parts"}


def make_agent(name: str, seed: int = 0, table: PatternTable | None = None) -> Agent:
    """Build the agent registered as ``name``.

    ``seed`` is used by random agents; ``table`` by the entropy agents (default: the
    cached table of the default word lists).
    """
    try:
        factory = AGENTS[name]
    except KeyError:
        raise ValueError(f"unknown agent {name!r}; choose from {', '.join(AGENTS)}") from None
    if table is None and name in NEEDS_TABLE:
        table = default_table()
    return factory(seed, table)


__all__ = ["AGENTS", "Agent", "EntropyAgent", "LetterFrequencyAgent", "RandomAgent", "default_table",
           "make_agent"]
