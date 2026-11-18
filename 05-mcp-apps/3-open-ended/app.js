// 05 MCP Apps · 3 · Open-ended — the generic host page (../web/host.js). Only the offered tool differs.
import { startMcpHost } from "/host/host.js";

startMcpHost({
  mode: "3 \u00b7 Open-ended",
  title: "Model-written HTML inside an MCP App: two sandboxes deep",
  blurb: "build_trip_widget returns raw HTML from the model. The host sandboxes the view; the view sandboxes the HTML again in a nested iframe. Two boundaries: the host's and the app's.",
  examples: ["Plan 3 days in Tokyo", "An interactive packing checklist for a ski trip", "A budget slider for a week in Bali"],
});
