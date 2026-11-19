"""Write the terminal transcripts in docs/demo/: watch, play, assist and the test run.

The interactive modes are run with scripted keyboard input; every typed answer is
echoed after its prompt, as it would appear in a terminal.
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import io
import random
import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wordle_tr.agents import make_agent  # noqa: E402
from wordle_tr.alphabet import normalize  # noqa: E402
from wordle_tr.constraints import Constraints, ContradictionError  # noqa: E402
from wordle_tr.feedback import ALL_GREEN, NUM_PATTERNS, feedback, filter_candidates, pattern_to_text  # noqa: E402
from wordle_tr.words import load_answers  # noqa: E402

PLAY = ROOT / "scripts" / "play.py"


def run_play(args: list[str], respond: Callable[[str], str | None] | None = None) -> str:
    """Run scripts/play.py in this process; ``respond(prompt)`` plays the keyboard."""
    out = io.StringIO()

    def fake_input(prompt: str = "") -> str:
        text = respond(prompt) if respond else None
        if text is None:
            raise EOFError
        print(prompt + text)
        return text

    saved = builtins.input, sys.argv
    builtins.input, sys.argv = fake_input, [str(PLAY), *args]
    try:
        with contextlib.redirect_stdout(out):
            runpy.run_path(str(PLAY), run_name="__main__")
    finally:
        builtins.input, sys.argv = saved
    return f"$ python scripts/play.py {' '.join(args)}\n{out.getvalue()}"


def play_session(seed: int) -> str:
    """A human-style game: one invalid word, then the entropy agent's guesses."""
    answers = load_answers()
    hidden = random.Random(seed).choice(answers)
    agent, candidates, plan = make_agent("entropy"), list(answers), ["kalemi"]
    while True:
        guess = agent.choose_guess([], candidates)
        plan.append(guess)
        if guess == hidden:
            break
        candidates = filter_candidates(candidates, guess, feedback(guess, hidden))
    typed = iter(plan)
    return run_play(["play", "--seed", str(seed), "--no-color"], lambda prompt: next(typed, None))


def assist_session(hidden: str) -> str:
    """Help with a game on another site whose hidden word is ``hidden``; one typo is corrected."""
    history: list[tuple[str, int]] = []
    state = {"word": "", "typo_done": False}

    def respond(prompt: str) -> str | None:
        if "word you tried" in prompt:
            return ""  # accept the suggestion
        if "colours for" in prompt:
            word = normalize(prompt.split("colours for", 1)[1].strip(" :"))
            true = feedback(word, hidden)
            if len(history) == 1 and not state["typo_done"]:  # a mistyped pattern on turn 2
                state["typo_done"] = True
                for p in range(NUM_PATTERNS):
                    try:
                        Constraints.from_history(history + [(word, p)])
                    except ContradictionError:
                        return pattern_to_text(p)
            history.append((word, true))
            return pattern_to_text(true)
        return None

    return run_play(["assist", "--no-color"], respond)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "demo", help="output folder")
    parser.add_argument("--skip-tests", action="store_true", help="do not record the test run")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    watch = "\n".join(run_play(["watch", "--agent", agent, "--word", "sayma", "--no-color"])
                      for agent in ("frequency", "entropy", "expectimax"))
    files = {
        "watch.txt": watch,
        "play.txt": play_session(seed=2026),
        "assist.txt": assist_session("kazak"),
    }
    if not args.skip_tests:
        tests = subprocess.run([sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider"], cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8")
        files["test_run.txt"] = "$ python -m pytest -v\n" + tests.stdout.replace(str(ROOT), ".")
    for name, text in files.items():
        (args.out_dir / name).write_text(text, encoding="utf-8")
        print(f"wrote {args.out_dir / name} ({text.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
