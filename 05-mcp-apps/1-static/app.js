// 05 MCP Apps · 1 · Static — the generic host page (../web/host.js). Only the offered tool differs.
import { startMcpHost } from "/host/host.js";

startMcpHost({
  mode: "1 \u00b7 Static",
  title: "A hand-written MCP App view; the host's model supplies the data",
  blurb: "The MCP server ships a hand-written view (ui://trip/card.html). The host's model calls show_trip_card with data; the host runs the view in a sandboxed iframe and passes it the result over the bridge. The button sends ui/message back into the chat.",
  examples: ["Plan 3 days in Tokyo", "Plan a long weekend in Rome", "4 days in Iceland in winter"],
});
