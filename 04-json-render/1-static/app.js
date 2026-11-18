// 04 json-render · 1 STATIC — the generic json-render page (../web/app.mjs, bundled); only server.py differs.
import { startJsonRenderDemo } from "/jr/dist/jr-app.js";

startJsonRenderDemo({
  mode: "1 · Static",
  title: "A hand-written json-render spec; the model fills only the state",
  blurb:
    "spec.json is written by hand. Its props read state ({\"$state\": \"/trip/title\"}) and one card repeats over /trip/days. The model only writes data; it streams in as JSONL patches after the fixed elements. Right: the same spec drawn by a Python terminal renderer.",
  examples: ["Plan 3 days in Tokyo", "Plan a long weekend in Rome", "4 days in Iceland in winter"],
});
