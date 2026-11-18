// 06 Harness · 2 · Declarative — the generic harness page (../web/harness-page.js).
import { startHarnessDemo } from "/harness/harness-page.js";

startHarnessDemo({
  mode: "2 \u00b7 Declarative",
  title: "The agent reads the files, then designs a catalog UI",
  blurb: "render_ui(spec_json) is validated against the shared catalog. If it is wrong, the errors come back as the TOOL RESULT and the agent fixes its own spec on the next step. Same agent also runs in the terminal.",
  examples: ["Summarize my trip spending", "What is still not booked?", "Show my bookings"],
});
