// Wordle feedback and pattern encoding (port of wordle_tr/feedback.py).
// A pattern is the base-3 number of the five colours, grey = 0, yellow = 1, green = 2,
// with the first letter as the most significant digit: 0..242, all green = 242.

import { WORD_LENGTH, toUpper } from "./alphabet";

export const GREY = 0;
export const YELLOW = 1;
export const GREEN = 2;
export const NUM_PATTERNS = 243;
export const ALL_GREEN = 242;

export type Color = typeof GREY | typeof YELLOW | typeof GREEN;
export type History = Array<[string, number]>;

/** Pattern of `guess` against `answer` with the standard two-pass duplicate rule. */
export function feedback(guess: string, answer: string): number {
  const g = [...guess];
  const a = [...answer];
  if (guess === answer) return ALL_GREEN;
  const unmatched: string[] = [];
  for (let i = 0; i < WORD_LENGTH; i++) if (g[i] !== a[i]) unmatched.push(a[i]);
  let pattern = 0;
  for (let i = 0; i < WORD_LENGTH; i++) {
    if (g[i] === a[i]) pattern = pattern * 3 + GREEN;
    else {
      const k = unmatched.indexOf(g[i]);
      if (k >= 0) {
        unmatched.splice(k, 1);
        pattern = pattern * 3 + YELLOW;
      } else pattern = pattern * 3;
    }
  }
  return pattern;
}

const counts = new Int8Array(32);

/** The same rule on letter codes: guess at codes G[g..g+5), answer at A[a..a+5). */
export function feedbackCodes(G: Uint8Array, g: number, A: Uint8Array, a: number): number {
  let greens = 0;
  for (let i = 0; i < WORD_LENGTH; i++) {
    if (G[g + i] === A[a + i]) greens |= 1 << i;
    else counts[A[a + i]]++;
  }
  let pattern = 0;
  for (let i = 0; i < WORD_LENGTH; i++) {
    if (greens & (1 << i)) pattern = pattern * 3 + GREEN;
    else {
      const c = G[g + i];
      if (counts[c] > 0) {
        counts[c]--;
        pattern = pattern * 3 + YELLOW;
      } else pattern = pattern * 3;
    }
  }
  for (let i = 0; i < WORD_LENGTH; i++) counts[A[a + i]] = 0;
  return pattern;
}

export function decodePattern(pattern: number): Color[] {
  const colors: Color[] = [];
  for (let i = 0; i < WORD_LENGTH; i++) {
    colors.unshift((pattern % 3) as Color);
    pattern = Math.floor(pattern / 3);
  }
  return colors;
}

export function encodeColors(colors: readonly number[]): number {
  if (colors.length !== WORD_LENGTH || colors.some((c) => c < 0 || c > 2)) throw new Error("bad colours");
  return colors.reduce((p, c) => p * 3 + c, 0);
}

const EMOJI = ["⬜", "🟨", "🟩"];
const EMOJI_CONTRAST = ["⬜", "🟦", "🟧"];

export function patternToEmoji(pattern: number, highContrast = false): string {
  const set = highContrast ? EMOJI_CONTRAST : EMOJI;
  return decodePattern(pattern).map((c) => set[c]).join("");
}

const PARSE: Record<string, Color> = { g: GREEN, "🟩": GREEN, y: YELLOW, "🟨": YELLOW, x: GREY, ".": GREY, "⬜": GREY, "⬛": GREY };

/** "ggy.." / "ggyxx" / emoji → pattern. */
export function parsePattern(text: string): number {
  const symbols = [...text.trim().toLowerCase()].filter((c) => c !== " " && c !== "️");
  if (symbols.length !== WORD_LENGTH || symbols.some((c) => !(c in PARSE))) throw new Error(`bad pattern: ${text}`);
  return encodeColors(symbols.map((c) => PARSE[c]));
}

export function filterCandidates(candidates: readonly string[], guess: string, pattern: number): string[] {
  return candidates.filter((w) => feedback(guess, w) === pattern);
}

export function upperWord(word: string): string {
  return toUpper(word);
}
