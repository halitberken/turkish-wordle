// The Play page: a 6 x 5 board, the Turkish keyboard, daily and practice games, statistics.

import { ALPHABET, WORD_LENGTH, normalize, toLower, toUpper } from "../core/alphabet";
import { ALL_GREEN, decodePattern, feedback, patternToEmoji } from "../core/feedback";
import { dailyIndex, dayNumber } from "./daily";
import { load, save } from "./storage";
import { STATES, el, prefersReducedMotion, setTile, sleep, toast, type TileState } from "./ui";

const MAX_GUESSES = 6;
const KEY_ROWS = ["ertyuıopğü", "asdfghjklşi", "zcvbnmöç"]; // Turkish Q layout without q, w, x
const SITE = "https://halitberken.github.io/turkish-wordle/";

interface Stats {
  played: number;
  wins: number;
  streak: number;
  maxStreak: number;
  distribution: number[];
  lastDaily: number;
}

interface Game {
  mode: "daily" | "practice";
  day: number;
  answer: string;
  guesses: string[];
  patterns: number[];
  current: string;
  over: boolean;
}

const emptyStats = (): Stats => ({ played: 0, wins: 0, streak: 0, maxStreak: 0, distribution: Array(MAX_GUESSES).fill(0), lastDaily: -1 });

export class PlayPage {
  private game!: Game;
  private rows: HTMLElement[] = [];
  private keys = new Map<string, HTMLButtonElement>();
  private busy = false;
  private stats: Stats = load("stats", emptyStats());

  constructor(
    private answers: string[],
    private allowed: Set<string>,
    private isActive: () => boolean,
    private contrast: () => boolean,
  ) {
    this.buildBoard();
    this.buildKeyboard();
    document.addEventListener("keydown", (event) => this.onKey(event));
    document.querySelectorAll<HTMLButtonElement>(".segmented button").forEach((button) =>
      button.addEventListener("click", () => (button.dataset.mode === "daily" ? this.startDaily() : this.startPractice())),
    );
    document.getElementById("new-game")!.addEventListener("click", () => this.startPractice());
    document.getElementById("dialog-new-game")!.addEventListener("click", () => {
      (document.getElementById("stats-dialog") as HTMLDialogElement).close();
      this.startPractice();
    });
    document.getElementById("share")!.addEventListener("click", () => this.share());
    document.getElementById("open-stats")!.addEventListener("click", () => this.showStats());

    const requested = normalize(new URLSearchParams(window.location.search).get("word") ?? "");
    if (requested && this.answers.includes(requested)) this.startPractice(requested);
    else this.startDaily();
  }

  // --- games

  startDaily(): void {
    const day = dayNumber();
    const saved = load<{ day: number; guesses: string[] }>("daily", { day: -1, guesses: [] });
    const answer = this.answers[dailyIndex(day, this.answers.length)];
    this.newGame("daily", answer, day, saved.day === day ? saved.guesses : []);
  }

  startPractice(answer?: string): void {
    const word = answer ?? this.answers[Math.floor(Math.random() * this.answers.length)];
    this.newGame("practice", word, -1, []);
  }

  private newGame(mode: Game["mode"], answer: string, day: number, previous: string[]): void {
    this.game = { mode, day, answer, guesses: [], patterns: [], current: "", over: false };
    this.rows.forEach((row) => row.querySelectorAll<HTMLElement>(".tile").forEach((t) => setTile(t, "")));
    this.keys.forEach((key) => delete key.dataset.state);
    document.querySelectorAll<HTMLButtonElement>(".segmented button").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    document.getElementById("new-game")!.hidden = mode === "daily";
    document.getElementById("play-label")!.textContent =
      mode === "daily" ? `Daily #${day + 1}: the same word for everyone today` : "Practice: a random word";
    for (const guess of previous) this.commit(guess, false);
  }

  // --- input

  private onKey(event: KeyboardEvent): void {
    if (!this.isActive() || event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target as HTMLElement;
    if (target.closest("input, select, textarea, dialog[open]")) return;
    if (event.key === "Enter") {
      event.preventDefault();
      this.submit();
    } else if (event.key === "Backspace") this.erase();
    else if ([...event.key].length === 1) {
      const letter = toLower(event.key); // Turkish rules: I → ı, İ → i
      if (ALPHABET.includes(letter)) this.type(letter);
    }
  }

  type(letter: string): void {
    const g = this.game;
    if (g.over || this.busy || [...g.current].length >= WORD_LENGTH) return;
    g.current += letter;
    const cell = this.cell(g.guesses.length, [...g.current].length - 1);
    setTile(cell, letter);
    cell.classList.remove("pop");
    void cell.offsetWidth;
    cell.classList.add("pop");
  }

  erase(): void {
    const g = this.game;
    if (g.over || this.busy || !g.current) return;
    const letters = [...g.current];
    letters.pop();
    g.current = letters.join("");
    setTile(this.cell(g.guesses.length, letters.length), "");
  }

  submit(): void {
    const g = this.game;
    if (g.over || this.busy) return;
    if ([...g.current].length < WORD_LENGTH) return this.reject("Not enough letters");
    if (!this.allowed.has(g.current)) return this.reject("Not in the word list");
    this.commit(g.current, true);
  }

  private reject(message: string): void {
    toast(message);
    const row = this.rows[this.game.guesses.length];
    row.classList.remove("shake");
    void row.offsetWidth;
    row.classList.add("shake");
  }

  private async commit(guess: string, animate: boolean): Promise<void> {
    const g = this.game;
    const pattern = feedback(guess, g.answer);
    const rowIndex = g.guesses.length;
    g.guesses.push(guess);
    g.patterns.push(pattern);
    g.current = "";
    g.over = pattern === ALL_GREEN || g.guesses.length === MAX_GUESSES;
    if (g.mode === "daily") save("daily", { day: g.day, guesses: g.guesses });
    const colors = decodePattern(pattern);
    const reveal = animate && !prefersReducedMotion();
    this.busy = reveal;
    [...guess].forEach((letter, i) => {
      const cell = this.cell(rowIndex, i);
      const show = () => setTile(cell, letter, STATES[colors[i]]);
      if (!reveal) return show();
      window.setTimeout(() => cell.classList.add("flip"), i * 140);
      window.setTimeout(show, i * 140 + 180);
      window.setTimeout(() => cell.classList.remove("flip"), i * 140 + 400);
    });
    if (reveal) await sleep(WORD_LENGTH * 140 + 300);
    this.busy = false;
    [...guess].forEach((letter, i) => this.markKey(letter, STATES[colors[i]]));
    if (g.over) this.finish(animate);
  }

  private finish(fresh: boolean): void {
    const g = this.game;
    const won = g.patterns[g.patterns.length - 1] === ALL_GREEN;
    const alreadyCounted = g.mode === "daily" && this.stats.lastDaily === g.day;
    if (fresh && !alreadyCounted) {
      const s = this.stats;
      s.played++;
      if (won) {
        s.wins++;
        s.streak++;
        s.maxStreak = Math.max(s.maxStreak, s.streak);
        s.distribution[g.guesses.length - 1]++;
      } else s.streak = 0;
      if (g.mode === "daily") s.lastDaily = g.day;
      save("stats", s);
    }
    if (fresh) {
      toast(won ? ["Brilliant!", "Excellent!", "Great!", "Well done!", "Good!", "Phew!"][g.guesses.length - 1]
        : `The word was ${toUpper(g.answer)}`, 2200);
      window.setTimeout(() => this.showStats(), 1200);
    }
  }

  // --- statistics and sharing

  showStats(): void {
    const g = this.game;
    const s = this.stats;
    const won = g.over && g.patterns[g.patterns.length - 1] === ALL_GREEN;
    document.getElementById("result-text")!.textContent = !g.over ? ""
      : won ? `Solved in ${g.guesses.length}/${MAX_GUESSES}.` : `The word was ${toUpper(g.answer)}.`;
    const pct = s.played ? Math.round((100 * s.wins) / s.played) : 0;
    document.getElementById("stats-grid")!.replaceChildren(
      ...[[s.played, "Played"], [pct, "Win %"], [s.streak, "Streak"], [s.maxStreak, "Best streak"]].map(([value, label]) =>
        el("div", {}, el("strong", { text: value }), el("span", { text: label }))),
    );
    const top = Math.max(1, ...s.distribution);
    document.getElementById("distribution")!.replaceChildren(
      ...s.distribution.map((count, i) => {
        const fill = el("span", { class: won && g.guesses.length === i + 1 ? "fill current" : "fill", text: count });
        fill.style.width = `${Math.max(8, (100 * count) / top)}%`;
        return el("div", { class: "bar" }, el("span", { text: i + 1 }), fill);
      }),
    );
    (document.getElementById("share") as HTMLButtonElement).disabled = !g.over;
    const dialog = document.getElementById("stats-dialog") as HTMLDialogElement;
    if (!dialog.open) dialog.showModal();
  }

  shareText(): string {
    const g = this.game;
    const won = g.patterns[g.patterns.length - 1] === ALL_GREEN;
    const title = g.mode === "daily" ? `Kelime Avı #${g.day + 1}` : "Kelime Avı (practice)";
    const grid = g.patterns.map((p) => patternToEmoji(p, this.contrast())).join("\n");
    return `${title} ${won ? g.guesses.length : "X"}/${MAX_GUESSES}\n\n${grid}\n${SITE}`;
  }

  private async share(): Promise<void> {
    const text = this.shareText();
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to the clipboard");
    } catch {
      window.prompt("Copy your result:", text);
    }
  }

  // --- building blocks

  private buildBoard(): void {
    const board = document.getElementById("board")!;
    for (let r = 0; r < MAX_GUESSES; r++) {
      const row = el("div", { class: "row", "aria-label": `Guess ${r + 1}` });
      for (let c = 0; c < WORD_LENGTH; c++) row.append(el("div", { class: "tile", role: "img", "aria-label": "empty" }));
      this.rows.push(row);
      board.append(row);
    }
  }

  private buildKeyboard(): void {
    const keyboard = document.getElementById("keyboard")!;
    KEY_ROWS.forEach((letters, r) => {
      const row = el("div", { class: "krow" });
      if (r === 2) row.append(this.keyButton("enter", "Enter", () => this.submit(), "wide"));
      for (const letter of letters) {
        const button = this.keyButton(letter, toUpper(letter), () => this.type(letter));
        this.keys.set(letter, button);
        row.append(button);
      }
      if (r === 2) row.append(this.keyButton("backspace", "⌫", () => this.erase(), "wide"));
      keyboard.append(row);
    });
  }

  private keyButton(name: string, label: string, action: () => void, extra = ""): HTMLButtonElement {
    const button = el("button", { class: `key ${extra}`.trim(), type: "button", "data-key": name, text: label,
      "aria-label": name === "backspace" ? "Delete" : label });
    button.addEventListener("click", () => {
      action();
      button.blur();
    });
    return button;
  }

  private markKey(letter: string, state: TileState): void {
    const key = this.keys.get(letter);
    if (!key) return;
    const rank = (s?: string) => (s ? STATES.indexOf(s as TileState) : -1);
    if (rank(state) > rank(key.dataset.state)) key.dataset.state = state;
  }

  private cell(row: number, col: number): HTMLElement {
    return this.rows[row].children[col] as HTMLElement;
  }
}
