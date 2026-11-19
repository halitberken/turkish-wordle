"""Agent registry: ``make_agent(name, seed)`` builds any registered agent."""

from __future__ import annotations

from collections.abc import Callable

from wordle_tr.agents.base import Agent
from wordle_tr.agents.baselines import LetterFrequencyAgent, RandomAgent

AGENTS: dict[str, Callable[[int], Agent]] = {
    "random": lambda seed: RandomAgent(seed),
    "frequency": lambda seed: LetterFrequencyAgent(),
}


def make_agent(name: str, seed: int = 0) -> Agent:
    """Build the agent registered as ``name``; ``seed`` is used by random agents."""
    try:
        factory = AGENTS[name]
    except KeyError:
        raise ValueError(f"unknown agent {name!r}; choose from {', '.join(AGENTS)}") from None
    return factory(seed)


__all__ = ["AGENTS", "Agent", "LetterFrequencyAgent", "RandomAgent", "make_agent"]
