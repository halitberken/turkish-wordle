// Turkish alphabet, Turkish-aware case conversion and normalisation (port of wordle_tr/alphabet.py).

export const ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz";
export const WORD_LENGTH = 5;
export const LETTER_INDEX: ReadonlyMap<string, number> = new Map([...ALPHABET].map((c, i) => [c, i]));

const CIRCUMFLEX: Record<string, string> = { â: "a", î: "i", û: "u" };

/** Lower case with Turkish rules: I → ı, İ → i. */
export function toLower(text: string): string {
  return text.normalize("NFC").toLocaleLowerCase("tr");
}

/** Upper case with Turkish rules: i → İ, ı → I. */
export function toUpper(text: string): string {
  return text.normalize("NFC").toLocaleUpperCase("tr");
}

/** Trim, lower-case (Turkish) and drop circumflexes: "  Kâğıt " → "kağıt". */
export function normalize(text: string): string {
  return [...toLower(text.trim())].map((c) => CIRCUMFLEX[c] ?? c).join("");
}

/** True if `word` is exactly 5 lower-case Turkish letters. */
export function isValidWord(word: string): boolean {
  const letters = [...word];
  return letters.length === WORD_LENGTH && letters.every((c) => LETTER_INDEX.has(c));
}

/** Compare two words in Turkish alphabetical order (c < ç < d, ı < i). */
export function compareTurkish(a: string, b: string): number {
  const x = [...a];
  const y = [...b];
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = (LETTER_INDEX.get(x[i]) ?? 99) - (LETTER_INDEX.get(y[i]) ?? 99);
    if (d !== 0) return d;
  }
  return x.length - y.length;
}

/** Letter codes 0..28 of every word, flattened: word i occupies [5i, 5i + 5). */
export function encodeWords(words: readonly string[]): Uint8Array {
  const codes = new Uint8Array(words.length * WORD_LENGTH);
  words.forEach((word, i) => {
    [...word].forEach((c, j) => {
      const code = LETTER_INDEX.get(c);
      if (code === undefined) throw new Error(`not a Turkish letter: ${c} in ${word}`);
      codes[i * WORD_LENGTH + j] = code;
    });
  });
  return codes;
}
