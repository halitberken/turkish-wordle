// The Assist page: help with a game played elsewhere. Enter each guess and its colours;
// the agent suggests the next guess, lists the remaining candidates and states what is known.

import { filterIds } from "../core/agents";
import { WORD_LENGTH, isValidWord, normalize, toUpper } from "../core/alphabet";
import { Constraints, ContradictionError } from "../core/constraints";
import { ALL_GREEN, encodeColors, type History } from "../core/feedback";
import type { AgentName, Solver } from "./solver";
import { STATES, chips, el, setTile, tile, tileRow, type TileState } from "./ui";

export class AssistPage {
  private history: History = [];
  private candidates: number[] = [];
  private colors: number[] = Array(WORD_LENGTH).fill(0);
  private request = 0;
  private suggestion = "";
  private agentSelect = document.getElementById("assist-agent") as HTMLSelectElement;
  private wordInput = document.getElementById("assist-word") as HTMLInputElement;
  private tiles: HTMLElement[] = [];
  private status = document.getElementById("assist-status")!;

  constructor(private solver: Solver) {
    const box = document.getElementById("assist-tiles")!;
    for (let i = 0; i < WORD_LENGTH; i++) {
      const t = tile("", "absent");
      t.setAttribute("role", "button");
      t.tabIndex = 0;
      t.addEventListener("click", () => this.cycle(i));
      t.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.cycle(i);
        }
      });
      this.tiles.push(t);
      box.append(t);
    }
    this.wordInput.addEventListener("input", () => this.renderEntry());
    this.wordInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.add();
    });
    document.getElementById("assist-add")!.addEventListener("click", () => this.add());
    document.getElementById("assist-undo")!.addEventListener("click", () => this.undo());
    document.getElementById("assist-reset")!.addEventListener("click", () => this.reset());
    this.agentSelect.addEventListener("change", () => this.suggest());
    this.reset();
  }

  private reset(): void {
    this.history = [];
    this.recompute();
  }

  private undo(): void {
    this.history.pop();
    this.recompute();
  }

  private recompute(): void {
    this.candidates = this.solver.allIds();
    for (const [guess, pattern] of this.history) this.candidates = filterIds(this.solver.ctx, this.candidates, guess, pattern);
    this.status.textContent = "";
    this.wordInput.value = "";
    this.colors.fill(0);
    this.renderEntry();
    this.render();
    this.suggest();
  }

  private cycle(i: number): void {
    this.colors[i] = (this.colors[i] + 1) % 3;
    this.renderEntry();
  }

  private renderEntry(): void {
    const letters = [...normalize(this.wordInput.value)];
    this.tiles.forEach((t, i) => {
      setTile(t, letters[i] ?? "", STATES[this.colors[i]] as TileState);
      t.setAttribute("aria-label", `${t.getAttribute("aria-label")}; tap to change the colour`);
    });
  }

  private add(): void {
    const word = normalize(this.wordInput.value);
    if (!isValidWord(word)) {
      this.status.textContent = "Type a word of 5 Turkish letters first.";
      return;
    }
    const pattern = encodeColors(this.colors);
    try {
      Constraints.fromHistory([...this.history, [word, pattern]]);
    } catch (error) {
      if (!(error instanceof ContradictionError)) throw error;
      this.status.replaceChildren(el("span", { class: "error", text: `Contradictory input: ${error.message}. Check the colours.` }));
      return;
    }
    if (pattern !== ALL_GREEN) {
      const remaining = filterIds(this.solver.ctx, this.candidates, word, pattern);
      if (!remaining.length) {
        this.status.replaceChildren(el("span", { class: "error",
          text: "Contradictory input: no word in our answer list fits all the colours. Check the colours." }));
        return;
      }
    }
    this.history.push([word, pattern]);
    this.recompute();
    if (pattern === ALL_GREEN) this.status.textContent = `Solved in ${this.history.length}!`;
    else if (!this.solver.ctx.guessIndex.has(word)) this.status.textContent = `Note: ${toUpper(word)} is not in our word list.`;
  }

  private render(): void {
    let ids = this.solver.allIds();
    document.getElementById("assist-rows")!.replaceChildren(
      ...this.history.map(([guess, pattern]) => {
        ids = filterIds(this.solver.ctx, ids, guess, pattern);
        const text = pattern === ALL_GREEN ? "solved" : `${ids.length.toLocaleString("en")} candidate${ids.length === 1 ? "" : "s"} left`;
        return el("li", {}, tileRow(guess, pattern), el("div", { class: "meta", text }));
      }),
    );
    const facts = document.getElementById("assist-facts")!;
    const solved = this.history.length > 0 && this.history[this.history.length - 1][1] === ALL_GREEN;
    if (!this.history.length || solved) {
      facts.replaceChildren();
      return;
    }
    const words = this.candidates.map((i) => this.solver.ctx.answers[i]);
    facts.replaceChildren(
      el("p", {}, el("strong", { text: "Known: " }), Constraints.fromHistory(this.history).describe()),
      el("p", {}, el("strong", { text: `${words.length.toLocaleString("en")} candidate${words.length === 1 ? "" : "s"} left` }),
        words.length > 20 ? " (first 20)" : ""),
      chips(words, 20),
    );
  }

  private async suggest(): Promise<void> {
    const box = document.getElementById("assist-suggestion")!;
    const solved = this.history.length > 0 && this.history[this.history.length - 1][1] === ALL_GREEN;
    if (solved) {
      box.replaceChildren(el("span", { class: "label", text: "Solved. Start over for a new game." }));
      return;
    }
    const request = ++this.request;
    box.replaceChildren(el("span", { class: "label", text: "Thinking…" }));
    const agent = this.agentSelect.value as AgentName;
    const choice = await this.solver.choose(agent, this.history, this.candidates);
    if (request !== this.request) return;
    this.suggestion = choice.guess;
    const use = el("button", { class: "button ghost", type: "button", text: "Use it" });
    use.addEventListener("click", () => {
      this.wordInput.value = toUpper(this.suggestion);
      this.renderEntry();
      this.wordInput.focus();
    });
    const detail = agent === "entropy" ? `${choice.bits.toFixed(2)} bits expected` : "most common letters";
    box.replaceChildren(
      el("span", { class: "label", text: "Try" }),
      el("div", { class: "tiles" }, ...[...choice.guess].map((c) => tile(c, undefined, true))),
      el("span", { class: "meta", text: detail }),
      use,
    );
  }
}
