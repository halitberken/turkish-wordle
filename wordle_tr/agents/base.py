"""The agent interface shared by every solver."""

from __future__ import annotations

from abc import ABC, abstractmethod

from wordle_tr.feedback import History


class Agent(ABC):
    """Chooses the next guess from the history and the current candidates.

    The game loop filters the candidates; agents never do it themselves.
    """

    name: str = "agent"
    deterministic: bool = True

    def reset(self) -> None:
        """Called before every new game."""

    @abstractmethod
    def choose_guess(self, history: History, candidates: list[str]) -> str:
        """Return the next guess. ``candidates`` is non-empty and in Turkish order."""
