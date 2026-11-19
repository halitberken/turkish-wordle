// Constraints implied by (guess, pattern) observations (port of wordle_tr/constraints.py).

import { ALPHABET, WORD_LENGTH, compareTurkish, toUpper } from "./alphabet";
import { GREEN, GREY, YELLOW, decodePattern, type History } from "./feedback";

export class ContradictionError extends Error {}

export class Constraints {
  fixed: (string | null)[] = Array(WORD_LENGTH).fill(null);
  forbidden: Set<string>[] = Array.from({ length: WORD_LENGTH }, () => new Set<string>());
  minCount = new Map<string, number>();
  maxCount = new Map<string, number>();

  static fromHistory(history: History): Constraints {
    const c = new Constraints();
    for (const [guess, pattern] of history) c.addObservation(guess, pattern);
    return c;
  }

  copy(): Constraints {
    const c = new Constraints();
    c.fixed = [...this.fixed];
    c.forbidden = this.forbidden.map((s) => new Set(s));
    c.minCount = new Map(this.minCount);
    c.maxCount = new Map(this.maxCount);
    return c;
  }

  /** Add one observation; throws ContradictionError and leaves `this` unchanged if impossible. */
  addObservation(guess: string, pattern: number): void {
    const letters = [...guess];
    const colors = decodePattern(pattern);
    checkPatternIsPossible(letters, colors);
    const next = this.copy();
    letters.forEach((letter, i) => {
      if (colors[i] === GREEN) {
        const current = next.fixed[i];
        if (current !== null && current !== letter) {
          throw new ContradictionError(`letter ${i + 1} cannot be both ${toUpper(current)} and ${toUpper(letter)}`);
        }
        next.fixed[i] = letter;
      } else next.forbidden[i].add(letter);
    });
    for (const letter of new Set(letters)) {
      const marks = colors.filter((_, i) => letters[i] === letter);
      const k = marks.filter((c) => c !== GREY).length;
      next.minCount.set(letter, Math.max(next.minCount.get(letter) ?? 0, k));
      if (marks.includes(GREY)) next.maxCount.set(letter, Math.min(next.maxCount.get(letter) ?? WORD_LENGTH, k));
    }
    next.check();
    Object.assign(this, next);
  }

  isSatisfied(word: string): boolean {
    const w = [...word];
    for (let i = 0; i < WORD_LENGTH; i++) {
      const f = this.fixed[i];
      if (f !== null && w[i] !== f) return false;
      if (this.forbidden[i].has(w[i])) return false;
    }
    for (const [letter, k] of this.minCount) if (count(w, letter) < k) return false;
    for (const [letter, k] of this.maxCount) if (count(w, letter) > k) return false;
    return true;
  }

  absentLetters(): Set<string> {
    return new Set([...this.maxCount].filter(([, k]) => k === 0).map(([c]) => c));
  }

  domains(): Set<string>[] {
    const absent = this.absentLetters();
    return this.fixed.map((f, i) =>
      f !== null ? new Set([f]) : new Set([...ALPHABET].filter((c) => !this.forbidden[i].has(c) && !absent.has(c))),
    );
  }

  /** Known facts in plain English, e.g. "Letter 1 is K; not in word: P; A is not elsewhere". */
  describe(): string {
    const facts: string[] = [];
    this.fixed.forEach((letter, i) => {
      if (letter !== null) facts.push(`letter ${i + 1} is ${toUpper(letter)}`);
    });
    const absent = [...this.absentLetters()].sort(compareTurkish);
    if (absent.length) facts.push("not in word: " + absent.map(toUpper).join(", "));
    const present = [...this.minCount].filter(([, k]) => k > 0).map(([c]) => c).sort(compareTurkish);
    for (const letter of present) {
      const placed = this.fixed.filter((f) => f === letter).length;
      const lo = this.minCount.get(letter) ?? 0;
      const hi = this.maxCount.get(letter) ?? WORD_LENGTH;
      const big = toUpper(letter);
      if (lo > placed) {
        let fact = `contains ${big}`;
        if (hi === lo) fact += " exactly " + times(lo);
        else if (lo > 1) fact += " at least " + times(lo);
        const excluded: number[] = [];
        for (let i = 0; i < WORD_LENGTH; i++) {
          if (this.forbidden[i].has(letter) && this.fixed[i] === null) excluded.push(i + 1);
        }
        if (excluded.length) fact += ", not as letter " + joinOr(excluded);
        facts.push(fact);
      } else if (hi === placed) facts.push(`${big} is not elsewhere`);
    }
    if (!facts.length) return "Nothing known yet";
    const text = facts.join("; ");
    return text[0].toUpperCase() + text.slice(1);
  }

  private check(): void {
    this.fixed.forEach((letter, i) => {
      if (letter !== null && this.forbidden[i].has(letter)) {
        throw new ContradictionError(`letter ${i + 1} cannot be both ${toUpper(letter)} and not ${toUpper(letter)}`);
      }
    });
    for (const [letter, k] of this.maxCount) {
      const lo = this.minCount.get(letter) ?? 0;
      if (lo > k) throw new ContradictionError(`${toUpper(letter)} must appear at least ${lo} and at most ${k} times`);
      if (this.fixed.filter((f) => f === letter).length > k) {
        throw new ContradictionError(`${toUpper(letter)} is fixed more often than it may appear`);
      }
    }
    if ([...this.minCount.values()].reduce((s, k) => s + k, 0) > WORD_LENGTH) {
      throw new ContradictionError(`more than ${WORD_LENGTH} letters are required`);
    }
    const domains = this.domains();
    domains.forEach((d, i) => {
      if (d.size === 0) throw new ContradictionError(`no letter is possible at position ${i + 1}`);
    });
    for (const [letter, k] of this.minCount) {
      if (domains.filter((d) => d.has(letter)).length < k) {
        throw new ContradictionError(`${toUpper(letter)} has no room left in the word`);
      }
    }
  }
}

function checkPatternIsPossible(letters: string[], colors: number[]): void {
  const seenGrey = new Set<string>();
  letters.forEach((letter, i) => {
    if (colors[i] === GREY) seenGrey.add(letter);
    else if (colors[i] === YELLOW && seenGrey.has(letter)) {
      throw new ContradictionError(
        `impossible pattern: the yellow ${toUpper(letter)} at letter ${i + 1} would have gone to the earlier grey ${toUpper(letter)}`,
      );
    }
  });
}

function count(word: string[], letter: string): number {
  return word.filter((c) => c === letter).length;
}

function times(n: number): string {
  return n === 1 ? "once" : n === 2 ? "twice" : `${n} times`;
}

function joinOr(numbers: number[]): string {
  const items = numbers.map(String);
  return items.length === 1 ? items[0] : items.slice(0, -1).join(", ") + " or " + items[items.length - 1];
}
