// 05 MCP Apps · 2 · Declarative — the generic host page (../web/host.js). Only the offered tool differs.
import { startMcpHost } from "/host/host.js";

startMcpHost({
  mode: "2 \u00b7 Declarative",
  title: "The MCP server asks a model for a catalog spec; its view renders it",
  blurb: "design_trip_screen asks Gemini (on the SERVER) for a validated catalog spec and returns it as structuredContent. The generic view ui://trip/genui.html renders it with the shared catalog renderer, pasted into the view.",
  examples: ["Plan 3 days in Tokyo", "Compare Lisbon and Barcelona for a cheap 4-day trip", "Weekend in New York with kids"],
});
