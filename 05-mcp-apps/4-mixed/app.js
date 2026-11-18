// 05 MCP Apps · 4 · Mixed — the generic host page (../web/host.js). Only the offered tool differs.
import { startMcpHost } from "/host/host.js";

startMcpHost({
  mode: "4 \u00b7 Mixed",
  title: "Catalog + one HtmlFrame inside an MCP App, with tool calls from the view",
  blurb: "plan_trip_mixed returns a spec with one HtmlFrame. Clicks call update_trip_screen THROUGH THE HOST (tools/call). That tool is visible to apps only, and the server checks the action against the screen it issued.",
  examples: ["Plan 3 days in Tokyo", "A 5-day Italy rail trip on a student budget", "Weekend hiking trip near Seattle"],
});
