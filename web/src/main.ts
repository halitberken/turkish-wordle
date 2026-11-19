// Kelime Avı: entry point. Loads the word data, applies the settings, and wires the pages.

import "./style.css";

import { renderAbout, type Summary } from "./app/about";
import { AssistPage } from "./app/assist";
import { PlayPage } from "./app/play";
import { Solver, type Openers } from "./app/solver";
import { load, save } from "./app/storage";
import { WatchPage } from "./app/watch";

const VIEWS = ["play", "watch", "assist", "about"] as const;
type View = (typeof VIEWS)[number];

interface Settings {
  theme: "system" | "light" | "dark";
  contrast: boolean;
}

const settings: Settings = load("settings", { theme: "system", contrast: false });

function applySettings(): void {
  const root = document.documentElement;
  if (settings.theme === "system") delete root.dataset.theme;
  else root.dataset.theme = settings.theme;
  if (settings.contrast) root.dataset.contrast = "high";
  else delete root.dataset.contrast;
  save("settings", settings);
}

function setupSettings(): void {
  const dialog = document.getElementById("settings-dialog") as HTMLDialogElement;
  document.getElementById("open-settings")!.addEventListener("click", () => dialog.showModal());
  for (const radio of document.querySelectorAll<HTMLInputElement>('input[name="theme"]')) {
    radio.checked = radio.value === settings.theme;
    radio.addEventListener("change", () => {
      settings.theme = radio.value as Settings["theme"];
      applySettings();
    });
  }
  const contrast = document.getElementById("contrast") as HTMLInputElement;
  contrast.checked = settings.contrast;
  contrast.addEventListener("change", () => {
    settings.contrast = contrast.checked;
    applySettings();
  });
}

function currentView(): View {
  const hash = window.location.hash.slice(1) as View;
  return VIEWS.includes(hash) ? hash : "play";
}

function showView(): void {
  const view = currentView();
  for (const name of VIEWS) document.getElementById(`view-${name}`)!.hidden = name !== view;
  for (const tab of document.querySelectorAll<HTMLAnchorElement>(".tabs a")) {
    tab.setAttribute("aria-selected", String(tab.dataset.view === view));
  }
}

async function fetchJson<T>(name: string): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${name}`);
  if (!response.ok) throw new Error(`could not load ${name}`);
  return (await response.json()) as T;
}

async function main(): Promise<void> {
  applySettings();
  setupSettings();
  showView();
  window.addEventListener("hashchange", showView);
  const [guesses, answers, openers, summary] = await Promise.all([
    fetchJson<string[]>("guesses.json"),
    fetchJson<string[]>("answers.json"),
    fetchJson<Openers>("openers.json"),
    fetchJson<Summary>("summary.json"),
  ]);
  const solver = new Solver({ guesses, answers }, openers);
  new PlayPage(answers, new Set(guesses), () => currentView() === "play", () => settings.contrast);
  new WatchPage(solver);
  new AssistPage(solver);
  renderAbout(summary);
  document.body.dataset.ready = "true";
}

main().catch((error) => {
  document.querySelector("main")!.textContent = `Kelime Avı could not start: ${error.message}`;
});
