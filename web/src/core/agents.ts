// The browser agents: letter frequency and entropy (ports of wordle_tr/agents/*.py).
// Candidates are answer ids (indices into the answer list, which is in Turkish order).

import { WORD_LENGTH, encodeWords } from "./alphabet";
import { NUM_PATTERNS, feedbackCodes } from "./feedback";

export interface WordData {
  guesses: string[];
  answers: string[];
}

export interface Context extends WordData {
  guessCodes: Uint8Array;
  answerCodes: Uint8Array;
  answerRow: Int32Array; // guess-list index of every answer
  guessIndex: Map<string, number>;
}

export interface Choice {
  guess: string;
  bits: number; // expected information of the guess (entropy agent)
  isCandidate: boolean;
}

export function buildContext(data: WordData): Context {
  const index = new Map(data.guesses.map((w, i) => [w, i]));
  const answerRow = Int32Array.from(data.answers, (w) => {
    const row = index.get(w);
    if (row === undefined) throw new Error(`answer ${w} is not a valid guess`);
    return row;
  });
  return { ...data, guessCodes: encodeWords(data.guesses), answerCodes: encodeWords(data.answers), answerRow,
    guessIndex: index };
}

/** Letter frequency: the candidate whose distinct letters occur in the most candidates (ties: Turkish order). */
export function frequencyChoice(ctx: Context, candidates: ArrayLike<number>): number {
  const counts = new Int32Array(32);
  const seen = new Int32Array(32).fill(-1);
  for (let k = 0; k < candidates.length; k++) {
    const base = candidates[k] * WORD_LENGTH;
    for (let i = 0; i < WORD_LENGTH; i++) {
      const c = ctx.answerCodes[base + i];
      if (seen[c] !== k) {
        seen[c] = k;
        counts[c]++;
      }
    }
  }
  let best = candidates[0];
  let bestScore = -1;
  for (let k = 0; k < candidates.length; k++) {
    const base = candidates[k] * WORD_LENGTH;
    let score = 0;
    for (let i = 0; i < WORD_LENGTH; i++) {
      const c = ctx.answerCodes[base + i];
      let first = true;
      for (let j = 0; j < i; j++) if (ctx.answerCodes[base + j] === c) first = false;
      if (first) score += counts[c];
    }
    if (score > bestScore) {
      bestScore = score;
      best = candidates[k];
    }
  }
  return best;
}

const LOG_TABLE_SIZE = 4096;
const xLog2x = Float64Array.from({ length: LOG_TABLE_SIZE }, (_, k) => (k > 1 ? k * Math.log2(k) : 0));

/** numpy's round(x, 9): scale, round half to even, scale back. */
function round9(x: number): number {
  const y = x * 1e9;
  let r = Math.round(y);
  if (Math.abs(y % 1) === 0.5 && r % 2 !== 0) r -= 1;
  return r / 1e9;
}

/** Entropy (bits) of the split of `candidates` by guess row `g`. */
export function entropyOf(ctx: Context, g: number, candidates: ArrayLike<number>, counts = new Int32Array(NUM_PATTERNS)): number {
  counts.fill(0);
  const n = candidates.length;
  for (let k = 0; k < n; k++) counts[feedbackCodes(ctx.guessCodes, g * WORD_LENGTH, ctx.answerCodes, candidates[k] * WORD_LENGTH)]++;
  let s = 0;
  for (let p = 0; p < NUM_PATTERNS; p++) s += xLog2x[counts[p]]; // ascending patterns, like the Python code
  return Math.max(Math.log2(n) - s / n, 0);
}

/**
 * Entropy agent: the guess (from the whole guess list) with the most expected information.
 * Ties go to candidates, then to Turkish order; with at most 2 candidates, the first candidate.
 */
export function entropyChoice(ctx: Context, candidates: ArrayLike<number>): Choice {
  const n = candidates.length;
  if (n <= 2) {
    const row = ctx.answerRow[candidates[0]];
    return { guess: ctx.guesses[row], bits: entropyOf(ctx, row, candidates), isCandidate: true };
  }
  const isCandidate = new Uint8Array(ctx.guesses.length);
  for (let k = 0; k < n; k++) isCandidate[ctx.answerRow[candidates[k]]] = 1;
  const counts = new Int32Array(NUM_PATTERNS);
  let best = -1;
  let bestRounded = -Infinity;
  let bestBits = 0;
  for (let g = 0; g < ctx.guesses.length; g++) {
    const bits = entropyOf(ctx, g, candidates, counts);
    const rounded = round9(bits);
    if (rounded > bestRounded || (rounded === bestRounded && isCandidate[g] && !isCandidate[best])) {
      best = g;
      bestRounded = rounded;
      bestBits = bits;
    }
  }
  return { guess: ctx.guesses[best], bits: bestBits, isCandidate: isCandidate[best] === 1 };
}

/** Answer ids that give `pattern` for `guess` (a word from the guess list). */
export function filterIds(ctx: Context, candidates: ArrayLike<number>, guess: string, pattern: number): number[] {
  const g = ctx.guessIndex.get(guess) ?? -1;
  const codes = g >= 0 ? ctx.guessCodes : encodeWords([guess]);
  const offset = g >= 0 ? g * WORD_LENGTH : 0;
  const kept: number[] = [];
  for (let k = 0; k < candidates.length; k++) {
    if (feedbackCodes(codes, offset, ctx.answerCodes, candidates[k] * WORD_LENGTH) === pattern) kept.push(candidates[k]);
  }
  return kept;
}
