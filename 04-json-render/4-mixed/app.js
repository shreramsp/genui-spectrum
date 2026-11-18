// 04 json-render · 4 MIXED — the generic json-render page with HtmlFrame and catalog actions.
import { startJsonRenderDemo } from "/jr/dist/jr-app.js";

startJsonRenderDemo({
  allowHtml: true,
  withActions: true,
  mode: "4 · Mixed",
  title: "Catalog components + one HtmlFrame, with catalog actions",
  blurb:
    "Actions are declared in the json-render catalog (cheaper, set_pace); the Button binds to one with an on.press field. Clicks in the button or the sandbox go back to the agent, which answers with only the JSONL patches that change the screen.",
  examples: ["Plan 3 days in Tokyo", "A 5-day Italy rail trip on a student budget", "Weekend hiking trip near Seattle"],
});
