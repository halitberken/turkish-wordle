// Small DOM helpers shared by the pages.

import { toUpper } from "../core/alphabet";
import { decodePattern } from "../core/feedback";

export const STATES = ["absent", "present", "correct"] as const;
export type TileState = (typeof STATES)[number];
const STATE_LABEL: Record<TileState, string> = { absent: "not in the word", present: "elsewhere", correct: "correct" };

type Attrs = Record<string, string | number | boolean | undefined>;

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Attrs = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === undefined || value === false) continue;
    if (name === "class") node.className = String(value);
    else if (name === "text") node.textContent = String(value);
    else node.setAttribute(name, value === true ? "" : String(value));
  }
  node.append(...children);
  return node;
}

export function tile(letter = "", state?: TileState, small = false): HTMLElement {
  const node = el("div", { class: small ? "tile small" : "tile", "data-letter": letter, role: "img" });
  setTile(node, letter, state);
  return node;
}

export function setTile(node: HTMLElement, letter: string, state?: TileState): void {
  node.textContent = letter ? toUpper(letter) : "";
  node.dataset.letter = letter;
  if (state) node.dataset.state = state;
  else delete node.dataset.state;
  node.setAttribute("aria-label", letter ? `${toUpper(letter)}${state ? ", " + STATE_LABEL[state] : ""}` : "empty");
}

/** A row of small tiles for a guess and its pattern. */
export function tileRow(word: string, pattern: number, small = true): HTMLElement {
  const colors = decodePattern(pattern);
  return el("div", { class: "tiles" }, ...[...word].map((c, i) => tile(c, STATES[colors[i]], small)));
}

export function chips(words: string[], limit: number): HTMLElement {
  const box = el("div", { class: "chips" }, ...words.slice(0, limit).map((w) => el("span", { class: "chip", text: toUpper(w) })));
  if (words.length > limit) box.append(el("span", { class: "chip", text: `+${words.length - limit} more` }));
  return box;
}

let toastTimer = 0;

export function toast(message: string, ms = 1800): void {
  const box = document.getElementById("toast")!;
  box.textContent = message;
  box.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => box.classList.remove("show"), ms);
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));
