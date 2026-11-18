// 03 OpenUI · 2 DECLARATIVE — the generic OpenUI page; the model writes the OpenUI Lang.
import { startOpenUiDemo } from "/openui/dist/openui-app.js";

startOpenUiDemo({
  mode: "2 · Declarative",
  title: "The model writes OpenUI Lang, rendered while it streams",
  blurb:
    "The system prompt is generated from the Zod catalog. The model's OpenUI Lang streams in and the official <Renderer> re-parses it on every piece: root appears first, children fill in as their lines arrive. The real OpenUI parser checks the result.",
  examples: ["Plan 3 days in Tokyo", "Compare Lisbon and Barcelona for a cheap 4-day trip", "Weekend in New York with kids"],
});
