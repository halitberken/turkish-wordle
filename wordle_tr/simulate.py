"""Playing agents against hidden words, and summarising the results."""

from __future__ import annotations

import random
import statistics
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from time import perf_counter

from wordle_tr.agents.base import Agent
from wordle_tr.alphabet import sort_key
from wordle_tr.feedback import History, feedback
from wordle_tr.filters import FilterFn, filter_reference
from wordle_tr.game import WordleGame

SAFETY_LIMIT = 100  # an agent that needs more guesses than this is broken

TurnCallback = Callable[[int, str, int, list[str]], None]


@dataclass
class GameResult:
    answer: str
    guesses: list[str] = field(default_factory=list)
    patterns: list[int] = field(default_factory=list)
    candidates_after: list[int] = field(default_factory=list)  # candidates left after each guess
    guess_times: list[float] = field(default_factory=list)  # seconds the agent spent per guess
    filter_times: list[float] = field(default_factory=list)  # seconds spent filtering per guess
    solved: bool = False

    @property
    def num_guesses(self) -> int:
        return len(self.guesses)


def play_game(
    agent: Agent,
    answer: str,
    answers: list[str],
    allowed: Iterable[str] | None = None,
    filter_fn: FilterFn = filter_reference,
    max_guesses: int | None = None,
    on_turn: TurnCallback | None = None,
) -> GameResult:
    """Let ``agent`` play one game; the loop (not the agent) filters the candidates
    with ``filter_fn(candidates, history)`` after every guess.

    ``on_turn(turn, guess, pattern, candidates)`` is called after every guess.
    """
    game = WordleGame(answer, allowed, max_guesses)
    agent.reset()
    candidates = list(answers)
    if game.answer not in candidates:
        raise ValueError(f"{answer!r} is not in the answer list")
    result = GameResult(answer=game.answer)
    while not game.over:
        if game.guesses_used >= SAFETY_LIMIT:
            raise RuntimeError(f"{agent.name} made no progress on {answer!r}")
        t0 = perf_counter()
        guess = agent.choose_guess(list(game.history), candidates)
        t1 = perf_counter()
        pattern = game.play(guess)
        guess = game.history[-1][0]
        t2 = perf_counter()
        candidates = filter_fn(candidates, game.history)
        t3 = perf_counter()
        result.guesses.append(guess)
        result.patterns.append(pattern)
        result.candidates_after.append(len(candidates))
        result.guess_times.append(t1 - t0)
        result.filter_times.append(t3 - t2)
        if on_turn is not None:
            on_turn(game.guesses_used, guess, pattern, candidates)
    result.solved = game.won
    return result


def evaluate(
    agent: Agent,
    answers: list[str],
    allowed: Iterable[str] | None = None,
    filter_fn: FilterFn = filter_reference,
    max_guesses: int | None = None,
    words: list[str] | None = None,
) -> list[GameResult]:
    """Play one game per hidden word in ``words`` (default: every answer)."""
    allowed_set = frozenset(allowed) if allowed is not None else None
    targets = answers if words is None else words
    return [play_game(agent, w, answers, allowed_set, filter_fn, max_guesses) for w in targets]


def random_histories(
    answers: list[str], guesses: list[str], n: int, seed: int, max_guesses: int = 4
) -> list[tuple[str, History]]:
    """``n`` random game states: a hidden answer and 1..max_guesses random guesses with their patterns."""
    rng = random.Random(seed)
    states = []
    for _ in range(n):
        answer = rng.choice(answers)
        history = [(g, feedback(g, answer)) for g in rng.sample(guesses, rng.randint(1, max_guesses))]
        states.append((answer, history))
    return states


@dataclass
class Summary:
    agent: str
    games: int
    mean: float  # mean number of guesses
    std: float  # standard deviation of the number of guesses (over games)
    limit: int
    within_limit_pct: float  # % of games solved within `limit` guesses
    failures: int  # games not solved within `limit` guesses
    max: int
    histogram: dict[int, int]  # number of guesses -> games
    mean_time_per_guess_ms: float  # agent thinking time
    mean_filter_time_ms: float  # candidate filtering time per guess
    total_time_s: float
    hardest: list[tuple[str, int]]  # (answer, guesses), most guesses first

    def to_dict(self) -> dict:
        data = asdict(self)
        data["histogram"] = {str(k): v for k, v in self.histogram.items()}
        data["hardest"] = [list(item) for item in self.hardest]
        return data


def aggregate(summaries: list[Summary]) -> dict:
    """Combine runs of one agent (e.g. several seeds): mean and sample std over runs."""

    def mean_std(values: list[float]) -> tuple[float, float]:
        return statistics.fmean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)

    mean, mean_std_ = mean_std([s.mean for s in summaries])
    within, within_std = mean_std([s.within_limit_pct for s in summaries])
    lengths = sorted({k for s in summaries for k in s.histogram})
    return {
        "runs": len(summaries),
        "mean": mean,
        "mean_std": mean_std_,
        "within_limit_pct": within,
        "within_limit_pct_std": within_std,
        "failures": statistics.fmean(s.failures for s in summaries),
        "max": max(s.max for s in summaries),
        "histogram": {str(k): statistics.fmean(s.histogram.get(k, 0) for s in summaries)
                      for k in lengths},
        "mean_time_per_guess_ms": statistics.fmean(s.mean_time_per_guess_ms for s in summaries),
        "mean_filter_time_ms": statistics.fmean(s.mean_filter_time_ms for s in summaries),
    }


def summarize(results: list[GameResult], agent: str = "", limit: int = 6, hardest: int = 10) -> Summary:
    """Aggregate statistics of a list of games."""
    counts = [r.num_guesses for r in results]
    guess_times = [t for r in results for t in r.guess_times]
    filter_times = [t for r in results for t in r.filter_times]
    within = sum(r.solved and r.num_guesses <= limit for r in results)
    ranked = sorted(results, key=lambda r: (-r.num_guesses, sort_key(r.answer)))
    return Summary(
        agent=agent,
        games=len(results),
        mean=statistics.fmean(counts),
        std=statistics.pstdev(counts),
        limit=limit,
        within_limit_pct=100.0 * within / len(results),
        failures=len(results) - within,
        max=max(counts),
        histogram=dict(sorted(Counter(counts).items())),
        mean_time_per_guess_ms=1000.0 * statistics.fmean(guess_times),
        mean_filter_time_ms=1000.0 * statistics.fmean(filter_times),
        total_time_s=sum(guess_times) + sum(filter_times),
        hardest=[(r.answer, r.num_guesses) for r in ranked[:hardest]],
    )
