// The "How it works" page: the problem, the methods and the headline results (summary.json).

import { toUpper } from "../core/alphabet";
import { el } from "./ui";

export interface Summary {
  answers: number;
  guesses: number;
  agents: { name: string; label: string; opener: string; mean: number; ci: [number, number]; within6: number; max: number }[];
  optimum: { lower: number; best: number; opener: string };
}

const REPO = "https://github.com/halitberken/turkish-wordle";

export function renderAbout(summary: Summary): void {
  const best = Math.min(...summary.agents.map((a) => a.mean));
  const rows = summary.agents.map((a) =>
    el("tr", { class: a.mean === best ? "best" : "" },
      el("td", { text: a.label }),
      el("td", { text: toUpper(a.opener) }),
      el("td", { class: "num", text: a.mean.toFixed(4) }),
      el("td", { class: "num", text: `${a.ci[0].toFixed(3)}–${a.ci[1].toFixed(3)}` }),
      el("td", { class: "num", text: `${a.within6.toFixed(2)} %` }),
      el("td", { class: "num", text: a.max }),
    ));
  const link = (href: string, text: string) => el("a", { href, text, target: "_blank", rel: "noopener" });
  const p = (...parts: (Node | string)[]) => el("p", {}, ...parts);

  document.getElementById("view-about")!.replaceChildren(
    el("h2", { text: "The game" }),
    p(`Guess a hidden five-letter Turkish word in at most six tries. After each guess, a letter turns
      turquoise if it is in the right place, saffron if it is in the word but somewhere else, and grey
      otherwise (repeated letters are coloured left to right, as long as copies remain). The word is one of
      ${summary.answers.toLocaleString("en")} common words; ${summary.guesses.toLocaleString("en")} dictionary
      words are accepted as guesses. Turkish has 29 letters, with dotted İ/i and dotless I/ı as different letters.`),
    el("h2", { text: "How the computer plays" }),
    el("ul", {},
      el("li", {}, el("strong", { text: "Constraints. " }), `Every coloured guess becomes constraints (a letter is here,
        is not there, appears at least or exactly k times). Finding the words that are still possible is a constraint
        satisfaction problem; a lookup table of all ${(summary.guesses * summary.answers).toLocaleString("en")} patterns makes it instant.`),
      el("li", {}, el("strong", { text: "Information. " }), `The entropy agent tries every allowed word and picks the one
        whose colours are expected to tell the most (in bits) about the hidden word. It may play a word that cannot be
        the answer if that word tests several letters at once.`),
      el("li", {}, el("strong", { text: "Search. " }), `The expectimax agent looks ahead over guesses and the colours
        they could produce, and minimises the expected number of guesses. An exact solver shows that it plays
        optimally after its first word, ${toUpper(summary.optimum.opener)}.`),
    ),
    p("This page runs the letter-frequency and entropy agents in your browser (Watch the AI, Assist)."),
    el("h2", { text: "Results" }),
    p(`Every agent played all ${summary.answers.toLocaleString("en")} answers (mean number of guesses, with a 95 %
      bootstrap interval):`),
    el("div", { class: "table-wrap" },
      el("table", {},
        el("thead", {}, el("tr", {},
          el("th", { text: "Agent" }), el("th", { text: "Opener" }), el("th", { class: "num", text: "Mean" }),
          el("th", { class: "num", text: "95 % CI" }), el("th", { class: "num", text: "≤ 6" }), el("th", { class: "num", text: "Max" }))),
        el("tbody", {}, ...rows))),
    p(`The best possible average over all openers lies between ${summary.optimum.lower} and ${summary.optimum.best}
      guesses (the latter reached with ${toUpper(summary.optimum.opener)}).`),
    el("h2", { text: "More" }),
    p("A term project for BIL 4112 Artificial Intelligence at Dokuz Eylül University (Berken, Arda, Faruk). ",
      link(REPO, "Source code"), " · ", link(`${REPO}/blob/main/docs/final_report.md`, "Final report"), "."),
  );
}
