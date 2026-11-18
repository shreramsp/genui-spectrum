// 06 Harness · 1 · Static — the generic harness page (../web/harness-page.js).
import { startHarnessDemo } from "/harness/harness-page.js";

startHarnessDemo({
  mode: "1 \u00b7 Static",
  title: "The agent reads the files, then picks a pre-built view",
  blurb: "A bounded agent loop: list_files and read_file on sample_trip/, then ONE render tool. Here the render tools are two pre-built views (show_budget, show_bookings). Watch the steps and tool calls in the log.",
  examples: ["Summarize my trip spending", "What is still not booked?", "Show my bookings"],
});
