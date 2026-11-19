"""Turkish Wordle in the terminal.

modes:
  play     you guess a hidden answer word (6 tries)
  watch    watch an agent solve a word, turn by turn
  assist   get suggestions while you play on another site

examples:
  python scripts/play.py play
  python scripts/play.py watch --agent frequency --word kalem
  python scripts/play.py assist --agent frequency
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_tr.agents import AGENTS, make_agent  # noqa: E402
from wordle_tr.alphabet import is_valid_word, normalize, to_upper  # noqa: E402
from wordle_tr.constraints import Constraints, ContradictionError  # noqa: E402
from wordle_tr.feedback import (  # noqa: E402
    ALL_GREEN,
    GREEN,
    GREY,
    YELLOW,
    filter_candidates,
    letter_states,
    parse_pattern,
    pattern_to_emoji,
    render_guess,
)
from wordle_tr.filters import FILTERS, make_filter  # noqa: E402
from wordle_tr.game import InvalidGuessError, WordleGame  # noqa: E402
from wordle_tr.simulate import play_game  # noqa: E402
from wordle_tr.words import load_answers, load_guesses  # noqa: E402

KEYBOARD = ["ertyuıopğü", "asdfghjklşi", "zcvbnmöç"]  # Turkish Q layout without q, w, x
QUIT = {"quit", "exit", "q"}


def use_color(args: argparse.Namespace) -> bool:
    return not args.no_color and sys.stdout.isatty() and "NO_COLOR" not in os.environ


def word_list(words: list[str], limit: int) -> str:
    shown = ", ".join(to_upper(w) for w in words[:limit])
    return shown + (f", … (+{len(words) - limit})" if len(words) > limit else "")


def render_keyboard(states: dict[str, int], color: bool) -> str:
    if not color:
        groups = {GREEN: [], YELLOW: [], GREY: []}
        for letter, state in states.items():
            groups[state].append(to_upper(letter))
        return (f"green: {' '.join(groups[GREEN]) or '-'}   yellow: {' '.join(groups[YELLOW]) or '-'}"
                f"   not in word: {' '.join(groups[GREY]) or '-'}")
    style = {GREEN: "\x1b[1;97;42m", YELLOW: "\x1b[1;30;43m", GREY: "\x1b[2;37;100m"}
    rows = []
    for indent, row in enumerate(KEYBOARD):
        keys = [f"{style[states[c]]}{to_upper(c)}\x1b[0m" if c in states else to_upper(c) for c in row]
        rows.append(" " * indent + " ".join(keys))
    return "\n".join(rows)


def pick_word(args: argparse.Namespace, answers: list[str]) -> tuple[str, int | None]:
    """The hidden word from --word, or a seeded random answer (seed printed for replay)."""
    if args.word:
        return normalize(args.word), None
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1_000_000)
    return random.Random(seed).choice(answers), seed


def cmd_play(args: argparse.Namespace) -> None:
    answers, guesses = load_answers(), load_guesses()
    color = use_color(args)
    answer, seed = pick_word(args, answers)
    if answer not in guesses:
        sys.exit(f"{args.word!r} is not in the word list")
    game = WordleGame(answer, guesses, args.max_guesses)
    print(f"Guess the 5-letter Turkish word in {args.max_guesses} tries"
          + (f" (game seed {seed})" if seed is not None else "") + ". Type 'quit' to give up.")
    while not game.over:
        try:
            text = input(f"\nGuess {game.guesses_used + 1}/{args.max_guesses}: ")
        except EOFError:
            break
        if text.strip().lower() in QUIT:
            break
        try:
            game.play(text)
        except InvalidGuessError as error:
            print(f"  {error}, try again")
            continue
        print()
        for guess, pattern in game.history:
            print("  " + render_guess(guess, pattern, color))
        print("\n" + render_keyboard(letter_states(game.history), color))
    if game.won:
        print(f"\nSolved in {game.guesses_used}/{args.max_guesses}!\n")
        print("\n".join(pattern_to_emoji(p) for _, p in game.history))
    else:
        print(f"\nThe word was {to_upper(game.answer)}.")


def cmd_watch(args: argparse.Namespace) -> None:
    answers, guesses = load_answers(), load_guesses()
    color = use_color(args)
    answer, seed = pick_word(args, answers)
    if answer not in answers:
        sys.exit(f"{args.word!r} is not in the answer list")
    agent = make_agent(args.agent, args.agent_seed)
    print(f"{args.agent} agent, hidden word {to_upper(answer)}"
          + (f" (word seed {seed})" if seed is not None else "") + f", {len(answers):,} candidates")

    def on_turn(turn: int, guess: str, pattern: int, candidates: list[str]) -> None:
        line = f"{turn:>2}. {render_guess(guess, pattern, color)}"
        if pattern != ALL_GREEN:
            line += f"   {len(candidates):,} candidate{'s' if len(candidates) != 1 else ''} left"
            if len(candidates) <= args.show:
                line += ": " + word_list(candidates, args.show)
        print(line)

    result = play_game(agent, answer, answers, guesses, make_filter(args.filter), args.max_guesses, on_turn)
    if result.solved:
        print(f"Solved in {result.num_guesses} guesses.")
    else:
        print(f"Not solved within {args.max_guesses} guesses.")


def ask(prompt: str) -> str | None:
    try:
        text = input(prompt).strip()
    except EOFError:
        return None
    return None if text.lower() in QUIT else text


def cmd_assist(args: argparse.Namespace) -> None:
    answers, guesses = load_answers(), load_guesses()
    color = use_color(args)
    agent = make_agent(args.agent, args.agent_seed)
    agent.reset()
    history: list[tuple[str, int]] = []
    candidates = list(answers)
    print("For each turn, type the word you tried (Enter = the suggestion) and the colours you got:\n"
          "g = green, y = yellow, x or . = grey (e.g. gyxxg; emoji work too). Type 'quit' to stop.")
    while True:
        suggestion = agent.choose_guess(list(history), candidates)
        print(f"\nTurn {len(history) + 1}: {len(candidates):,} candidate{'s' if len(candidates) != 1 else ''}"
              f" left. Suggestion: {to_upper(suggestion)}")
        text = ask("  word you tried: ")
        if text is None:
            return
        word = normalize(text) if text else suggestion
        if not is_valid_word(word):
            print(f"  {text!r} is not 5 Turkish letters, try again")
            continue
        if word not in guesses:
            print(f"  note: {to_upper(word)} is not in our word list (used anyway)")
        text = ask(f"  colours for {to_upper(word)}: ")
        if text is None:
            return
        try:
            pattern = parse_pattern(text)
            constraints = Constraints.from_history(history + [(word, pattern)])
        except ContradictionError as error:
            print(f"  Contradictory input: {error}. Enter this turn again.")
            continue
        except ValueError as error:
            print(f"  {error}")
            continue
        if pattern == ALL_GREEN:
            print(f"  Solved in {len(history) + 1}!")
            return
        remaining = filter_candidates(candidates, word, pattern)
        if not remaining:
            print("  Contradictory input: no word in the answer list fits all the colours so far. "
                  "Enter this turn again.")
            continue
        history.append((word, pattern))
        candidates = remaining
        print("  " + render_guess(word, pattern, color))
        print(f"  Known: {constraints.describe()}")
        if len(candidates) <= args.show:
            print(f"  Candidates: {word_list(candidates, args.show)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--no-color", action="store_true", help="plain text and emoji instead of ANSI colours")

    p = sub.add_parser("play", help="guess a hidden word yourself")
    p.add_argument("--word", help="hidden word (default: a random answer)")
    p.add_argument("--seed", type=int, help="seed for choosing the random word")
    p.add_argument("--max-guesses", type=int, default=6, help="number of tries (default 6)")
    common(p)
    p.set_defaults(func=cmd_play)

    p = sub.add_parser("watch", help="watch an agent solve a word")
    p.add_argument("--agent", choices=sorted(AGENTS), default="frequency", help="agent (default frequency)")
    p.add_argument("--word", help="hidden word (default: a random answer)")
    p.add_argument("--seed", type=int, help="seed for choosing the random word")
    p.add_argument("--agent-seed", type=int, default=0, help="seed for random agents (default 0)")
    p.add_argument("--filter", choices=sorted(FILTERS), default="feedback", help="candidate filter")
    p.add_argument("--max-guesses", type=int, default=None, help="guess limit (default: unlimited)")
    p.add_argument("--show", type=int, default=10, help="list the candidates when at most this many remain")
    common(p)
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("assist", help="suggestions while you play on another site")
    p.add_argument("--agent", choices=sorted(AGENTS), default="frequency", help="agent (default frequency)")
    p.add_argument("--agent-seed", type=int, default=0, help="seed for random agents (default 0)")
    p.add_argument("--show", type=int, default=20, help="list the candidates when at most this many remain")
    common(p)
    p.set_defaults(func=cmd_assist)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
