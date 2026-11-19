// Web Worker: scores every guess for the entropy agent, so the page stays responsive.

import { buildContext, entropyChoice, type Context, type WordData } from "../core/agents";

type Request = { type: "init"; data: WordData } | { type: "choose"; id: number; candidates: number[] };

let ctx: Context | null = null;
const post = (message: unknown) => (self as unknown as { postMessage(m: unknown): void }).postMessage(message);

self.onmessage = (event: MessageEvent<Request>) => {
  const message = event.data;
  if (message.type === "init") {
    ctx = buildContext(message.data);
  } else if (message.type === "choose" && ctx) {
    post({ id: message.id, choice: entropyChoice(ctx, message.candidates) });
  }
};
