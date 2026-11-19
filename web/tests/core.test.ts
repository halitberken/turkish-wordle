import { describe, expect, it } from "vitest";

import agentFixtures from "../public/data/agent_fixtures.json";
import answers from "../public/data/answers.json";
import fixtures from "../public/data/feedback_fixtures.json";
import guesses from "../public/data/guesses.json";
import openers from "../public/data/openers.json";
import { buildContext, entropyChoice, filterIds, frequencyChoice } from "../src/core/agents";
import { ALPHABET, compareTurkish, encodeWords, isValidWord, normalize, toLower, toUpper } from "../src/core/alphabet";
import { Constraints, ContradictionError } from "../src/core/constraints";
import {
  ALL_GREEN,
  decodePattern,
  encodeColors,
  feedback,
  feedbackCodes,
  filterCandidates,
  parsePattern,
  patternToEmoji,
  type History,
} from "../src/core/feedback";

const ctx = buildContext({ guesses, answers });

describe("Turkish alphabet", () => {
  it("has 29 letters and Turkish case rules", () => {
    expect([...ALPHABET]).toHaveLength(29);
    expect(toLower("İSTANBUL")).toBe("istanbul");
    expect(toLower("IŞIK")).toBe("ışık");
    expect(toUpper("ılık")).toBe("ILIK");
    expect(toUpper("istanbul")).toBe("İSTANBUL");
    expect([...ALPHABET].every((c) => toLower(toUpper(c)) === c)).toBe(true);
  });

  it("normalises and validates words", () => {
    expect(normalize("  Kâğıt ")).toBe("kağıt");
    expect(normalize("hâlâ")).toBe("hala");
    expect(normalize(" KILIÇ ")).toBe("kılıç");
    expect(isValidWord("ışığı")).toBe(true);
    expect(["kale", "kalemi", "Kalem", "quest", "kâlem"].some(isValidWord)).toBe(false);
  });

  it("sorts in Turkish order", () => {
    expect(["i", "ı", "d", "ç", "c"].sort(compareTurkish)).toEqual(["c", "ç", "d", "ı", "i"]);
    expect([...answers].sort(compareTurkish)).toEqual(answers);
  });
});

describe("feedback", () => {
  it("matches every Python triple", () => {
    for (const [guess, answer, pattern] of fixtures.triples as [string, string, number][]) {
      expect(feedback(guess, answer)).toBe(pattern);
      const g = encodeWords([guess]);
      const a = encodeWords([answer]);
      expect(feedbackCodes(g, 0, a, 0)).toBe(pattern);
    }
  });

  it("handles the duplicate-letter cases", () => {
    for (const c of fixtures.cases) {
      expect(feedback(c.guess, c.answer)).toBe(c.pattern);
      expect(patternToEmoji(c.pattern)).toBe(c.emoji);
    }
    expect(feedback("kalem", "kalem")).toBe(ALL_GREEN);
  });

  it("encodes and parses patterns", () => {
    for (let p = 0; p < 243; p++) expect(encodeColors(decodePattern(p))).toBe(p);
    expect(parsePattern("ggy..")).toBe(encodeColors([2, 2, 1, 0, 0]));
    expect(parsePattern("🟩🟩🟨⬜⬜")).toBe(encodeColors([2, 2, 1, 0, 0]));
    expect(() => parsePattern("ggyx")).toThrow();
  });

  it("filtering keeps the answer", () => {
    for (const [guess, answer, pattern] of (fixtures.triples as [string, string, number][]).slice(0, 300)) {
      const kept = filterCandidates(answers, guess, pattern);
      expect(kept).toContain(answer);
      expect(filterIds(ctx, answers.map((_, i) => i), guess, pattern).map((i) => answers[i])).toEqual(kept);
    }
  });
});

describe("constraints", () => {
  it("describes what is known exactly like Python", () => {
    for (const item of fixtures.describe) {
      expect(Constraints.fromHistory(item.history as History).describe()).toBe(item.text);
    }
  });

  it("detects contradictory feedback", () => {
    for (const history of fixtures.contradictions) {
      expect(() => Constraints.fromHistory(history as History)).toThrow(ContradictionError);
    }
  });

  it("agrees with the feedback filter", () => {
    for (const item of fixtures.describe.slice(0, 30)) {
      const history = item.history as History;
      const constraints = Constraints.fromHistory(history);
      const byFeedback = answers.filter((w) => history.every(([g, p]) => feedback(g, w) === p));
      expect(answers.filter((w) => constraints.isSatisfied(w))).toEqual(byFeedback);
    }
  });
});

describe("agents", () => {
  const all = answers.map((_, i) => i);

  it("the frequency agent opens like Python", () => {
    expect(answers[frequencyChoice(ctx, all)]).toBe(openers.frequency.first);
  });

  it("the entropy agent picks the same first guess as Python", () => {
    const choice = entropyChoice(ctx, all);
    expect(choice.guess).toBe(openers.entropy.first);
    expect(choice.bits).toBeCloseTo(openers.entropy.bits, 5);
  });

  it("the entropy agent picks the same second guess for every first pattern", () => {
    const first = openers.entropy.first;
    for (const [pattern, expected] of Object.entries(openers.entropy.second)) {
      const candidates = filterIds(ctx, all, first, Number(pattern));
      expect(candidates).toHaveLength(expected.candidates);
      const choice = entropyChoice(ctx, candidates);
      expect(choice.guess).toBe(expected.guess);
      expect(choice.bits).toBeCloseTo(expected.bits, 5);
    }
  });

  it.each(["frequency", "entropy"] as const)("the %s agent plays the same games as Python", (name) => {
    const expected = agentFixtures.games[name];
    agentFixtures.words.forEach((secret, w) => {
      let candidates = all;
      const played: string[] = [];
      for (let turn = 0; turn < 20; turn++) {
        const second = openers.entropy.second as Record<string, { guess: string }>;
        const guess = turn === 0 ? openers[name].first
          : name === "frequency" ? answers[frequencyChoice(ctx, candidates)]
          : turn === 1 ? second[String(feedback(played[0], secret))].guess // checked in the test above
          : entropyChoice(ctx, candidates).guess;
        played.push(guess);
        if (guess === secret) break;
        candidates = filterIds(ctx, candidates, guess, feedback(guess, secret));
      }
      expect(played).toEqual(expected[w]);
    });
  });
});
