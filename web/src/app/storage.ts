// localStorage that never breaks the page: blocked or full storage just means nothing is remembered.

const PREFIX = "kelime-avi:";

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : { ...fallback, ...(JSON.parse(raw) as T) };
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // storage blocked (private mode, disabled cookies): keep playing without it
  }
}
