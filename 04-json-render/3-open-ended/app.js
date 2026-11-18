// 04 json-render · 3 OPEN-ENDED — the generic json-render page with HtmlFrame in the catalog.
import { startJsonRenderDemo } from "/jr/dist/jr-app.js";

startJsonRenderDemo({
  allowHtml: true,
  mode: "3 · Open-ended",
  title: "Model-written HTML as one json-render HtmlFrame element",
  blurb:
    "json-render only draws catalog components, so open-ended UI needs a catalog entry: HtmlFrame, whose renderer runs the HTML in a sandbox. Note the terminal pane: a target without a browser cannot run it.",
  examples: ["Plan 3 days in Tokyo", "An interactive packing checklist for a ski trip", "A budget slider for a week in Bali"],
});
