// The agents as the pages use them: precomputed openings, the frequency agent on the main
// thread, and the entropy agent in a Web Worker (with a main-thread fallback).

import { buildContext, entropyChoice, frequencyChoice, type Choice, type Context, type WordData } from "../core/agents";
import type { History } from "../core/feedback";

export type AgentName = "entropy" | "frequency";

export interface Openers {
  frequency: { first: string };
  entropy: { first: string; bits: number; second: Record<string, { guess: string; bits: number; candidates: number }> };
}

export class Solver {
  readonly ctx: Context;
  private worker: Worker | null = null;
  private pending = new Map<number, (choice: Choice) => void>();
  private nextId = 1;

  constructor(data: WordData, private openers: Openers) {
    this.ctx = buildContext(data);
    try {
      this.worker = new Worker(new URL("../workers/entropy.worker.ts", import.meta.url), { type: "module" });
      this.worker.onmessage = (event: MessageEvent<{ id: number; choice: Choice }>) => {
        this.pending.get(event.data.id)?.(event.data.choice);
        this.pending.delete(event.data.id);
      };
      this.worker.postMessage({ type: "init", data });
    } catch {
      this.worker = null;
    }
  }

  allIds(): number[] {
    return this.ctx.answers.map((_, i) => i);
  }

  /** The agent's next guess for the candidates (answer ids, ascending) after `history`. */
  async choose(agent: AgentName, history: History, candidates: number[]): Promise<Choice> {
    const all = candidates.length === this.ctx.answers.length;
    if (agent === "frequency") {
      const guess = history.length === 0 && all ? this.openers.frequency.first
        : this.ctx.answers[frequencyChoice(this.ctx, candidates)];
      return { guess, bits: 0, isCandidate: true };
    }
    const entropy = this.openers.entropy;
    if (history.length === 0 && all) return { guess: entropy.first, bits: entropy.bits, isCandidate: false };
    if (history.length === 1 && history[0][0] === entropy.first) {
      const second = entropy.second[String(history[0][1])];
      if (second && second.candidates === candidates.length) {
        const row = this.ctx.guessIndex.get(second.guess) ?? -1;
        const isCandidate = candidates.some((id) => this.ctx.answerRow[id] === row);
        return { guess: second.guess, bits: second.bits, isCandidate };
      }
    }
    if (!this.worker) return entropyChoice(this.ctx, candidates);
    const id = this.nextId++;
    return new Promise((resolve) => {
      this.pending.set(id, resolve);
      this.worker!.postMessage({ type: "choose", id, candidates });
    });
  }
}
