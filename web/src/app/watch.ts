// The "Watch the AI" page: an agent plays a chosen (or random) hidden word, guess by guess.

import { filterIds } from "../core/agents";
import { normalize, toUpper } from "../core/alphabet";
import { ALL_GREEN, feedback, type History } from "../core/feedback";
import type { AgentName, Solver } from "./solver";
import { chips, el, sleep, tileRow } from "./ui";

export class WatchPage {
  private answer = "";
  private history: History = [];
  private candidates: number[] = [];
  private run = 0; // increases on every restart, to stop an auto-play in progress
  private agentSelect = document.getElementById("watch-agent") as HTMLSelectElement;
  private wordInput = document.getElementById("watch-word") as HTMLInputElement;
  private status = document.getElementById("watch-status")!;
  private rows = document.getElementById("watch-rows")!;

  constructor(private solver: Solver) {
    document.getElementById("watch-random")!.addEventListener("click", () => {
      const answers = solver.ctx.answers;
      this.wordInput.value = toUpper(answers[Math.floor(Math.random() * answers.length)]);
      this.restart();
    });
    document.getElementById("watch-step")!.addEventListener("click", () => this.step());
    document.getElementById("watch-play")!.addEventListener("click", () => this.playAll());
    document.getElementById("watch-reset")!.addEventListener("click", () => this.restart());
    this.agentSelect.addEventListener("change", () => this.restart());
    this.wordInput.addEventListener("change", () => this.restart());
    this.wordInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.step();
    });
    this.wordInput.value = "SAYMA";
    this.restart();
  }

  private restart(): boolean {
    this.run++;
    this.rows.replaceChildren();
    this.history = [];
    this.candidates = this.solver.allIds();
    const word = normalize(this.wordInput.value);
    if (!this.solver.ctx.answers.includes(word)) {
      this.answer = "";
      this.status.textContent = word ? `${toUpper(word)} is not in the answer list; choose another word.` : "Choose a hidden word.";
      return false;
    }
    this.answer = word;
    this.status.textContent = `Hidden word ${toUpper(word)}: ${this.candidates.length.toLocaleString("en")} candidates.`;
    return true;
  }

  private solved(): boolean {
    return this.history.length > 0 && this.history[this.history.length - 1][1] === ALL_GREEN;
  }

  async step(): Promise<boolean> {
    if (!this.answer && !this.restart()) return false;
    if (this.solved()) return false;
    const run = this.run;
    const agent = this.agentSelect.value as AgentName;
    this.status.textContent = "Thinking…";
    const choice = await this.solver.choose(agent, this.history, this.candidates);
    if (run !== this.run) return false;
    const pattern = feedback(choice.guess, this.answer);
    this.history.push([choice.guess, pattern]);
    this.candidates = filterIds(this.solver.ctx, this.candidates, choice.guess, pattern);
    const left = this.candidates.length;
    const meta = el("div", { class: "meta" });
    if (agent === "entropy") meta.append(el("strong", { text: `${choice.bits.toFixed(2)} bits` }), " expected · ");
    if (pattern === ALL_GREEN) meta.append(el("strong", { text: "solved" }));
    else {
      meta.append(`${left.toLocaleString("en")} candidate${left === 1 ? "" : "s"} left`);
      if (left <= 12) meta.append(chips(this.solver.ctx.answers.filter((_, i) => this.candidates.includes(i)), 12));
    }
    this.rows.append(el("li", {}, tileRow(choice.guess, pattern), meta));
    this.status.textContent = pattern === ALL_GREEN
      ? `Solved in ${this.history.length} guess${this.history.length === 1 ? "" : "es"}.` : "";
    return pattern !== ALL_GREEN;
  }

  private async playAll(): Promise<void> {
    if (this.solved()) this.restart();
    const run = this.run;
    while (run === this.run && (await this.step())) await sleep(500);
  }
}
