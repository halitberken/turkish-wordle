import { defineConfig } from "vitest/config";

// The site is served from https://halitberken.github.io/turkish-wordle/ (GitHub Pages project site).
export default defineConfig({
  base: "/turkish-wordle/",
  build: { target: "es2022" },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
    testTimeout: 60_000,
  },
});
