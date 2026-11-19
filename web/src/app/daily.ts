// The daily word: the same for everyone, from the date in Turkey (UTC+3), through a fixed shuffle.

const DAY_MS = 86_400_000;
const TURKEY_OFFSET_MS = 3 * 3_600_000;
const FIRST_DAY = Date.UTC(2026, 0, 1);
const SHUFFLE_SEED = 20260101;

/** Days since 1 January 2026 in Turkish time; puzzle number = day + 1. */
export function dayNumber(now: number = Date.now()): number {
  return Math.floor((now + TURKEY_OFFSET_MS - FIRST_DAY) / DAY_MS);
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

let order: number[] = [];

/** Index into the answer list for a given day (a fixed random order, repeating after every answer). */
export function dailyIndex(day: number, count: number): number {
  if (order.length !== count) {
    const random = mulberry32(SHUFFLE_SEED);
    order = Array.from({ length: count }, (_, i) => i);
    for (let i = count - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
  }
  return order[((day % count) + count) % count];
}
