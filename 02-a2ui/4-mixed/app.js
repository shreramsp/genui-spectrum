// 02 A2UI · 4 MIXED — same generic A2UI page; Basic components + one HtmlFrame, actions round-trip.
import { startA2uiDemo } from "/a2ui/demo.js";

startA2uiDemo({
  mode: "4 · Mixed",
  title: "Basic Catalog components + one HtmlFrame, with actions",
  blurb:
    "Validated A2UI components plus one sandboxed HtmlFrame (pink border). Clicks in either send an A2UI action. The server checks it against its own copy of the screen, and the reply resends only the changed components (upsert by id) and the new data.",
  examples: ["Plan 3 days in Tokyo", "A 5-day Italy rail trip on a student budget", "Weekend hiking trip near Seattle"],
});
