// 03 OpenUI · 4 MIXED — the generic OpenUI page with HtmlArtifact enabled; actions round-trip.
import { startOpenUiDemo } from "/openui/dist/openui-app.js";

startOpenUiDemo({
  allowHtml: true,
  mode: "4 · Mixed",
  title: "Catalog components + one HtmlArtifact, with statement patches",
  blurb:
    "Model-written OpenUI Lang with one sandboxed HtmlArtifact (pink border). A click in either sends an action; the server allow-lists it, the model resends only the changed statements, and the page merges them with mergeStatements().",
  examples: ["Plan 3 days in Tokyo", "A 5-day Italy rail trip on a student budget", "Weekend hiking trip near Seattle"],
});
