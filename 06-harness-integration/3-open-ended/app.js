// 06 Harness · 3 · Open-ended — the generic harness page (../web/harness-page.js).
import { startHarnessDemo } from "/harness/harness-page.js";

startHarnessDemo({
  mode: "3 \u00b7 Open-ended",
  title: "The agent reads the files, then writes its own HTML",
  blurb: "render_html(html): the agent writes an interactive widget from the real numbers in expenses.csv. It runs in the sandbox; in the terminal surface it can only be described.",
  examples: ["Summarize my trip spending", "What is still not booked?", "Show my bookings"],
});
