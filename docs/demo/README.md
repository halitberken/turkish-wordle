# Terminal demo

Transcripts of the terminal tools, recorded by `python scripts/make_demo.py`
(scripted keyboard input; the typed text is shown after each prompt):

| File | What it shows |
| --- | --- |
| [`watch.txt`](watch.txt) | `play.py watch` for SAYMA with the letter-frequency (8 guesses), entropy (3) and expectimax (4) agents |
| [`play.txt`](play.txt) | `play.py play`: a game in the terminal, including a rejected invalid word and the shareable emoji grid |
| [`assist.txt`](assist.txt) | `play.py assist`: suggestions for a game on another site (hidden word KAZAK), with a mistyped pattern that is detected as contradictory |
| [`test_run.txt`](test_run.txt) | `python -m pytest -v`: the whole test suite |
| [`clean_clone_check.txt`](clean_clone_check.txt) | the hand-in check: fresh clone, fresh virtual environment, tests and every script of the README |

The transcripts use `--no-color`, so tiles appear as emoji (⬜🟨🟩). In a
terminal without that flag, `play.py` draws coloured tiles and a Turkish
keyboard with ANSI colours.

`watch.txt`:

```text
$ python scripts/play.py watch --agent entropy --word sayma --no-color
entropy agent, hidden word SAYMA, 1,900 candidates
 1. KAMER  ⬜🟩🟨⬜⬜  5.77 bits   51 candidates left
 2. SALYA  🟩🟩⬜🟨🟩  4.10 bits   1 candidate left: SAYMA
 3. SAYMA  🟩🟩🟩🟩🟩  0.00 bits
Solved in 3 guesses.
```
