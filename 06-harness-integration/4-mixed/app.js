// 06 Harness · 4 · Mixed — the generic harness page (../web/harness-page.js).
import { startHarnessDemo } from "/harness/harness-page.js";

startHarnessDemo({
  mode: "4 \u00b7 Mixed",
  title: "Catalog UI + one HtmlFrame; clicks go back into the agent loop",
  blurb: "Clicks are checked against the actions the UI offered, then added to the SAME conversation. The agent can read more files (here bookings.csv) before it re-renders.",
  examples: ["Summarize my trip spending", "What is still not booked?", "Show my bookings"],
});
