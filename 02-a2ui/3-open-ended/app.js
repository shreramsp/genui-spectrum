// 02 A2UI · 3 OPEN-ENDED — same generic A2UI page; the surface uses our custom catalog with HtmlFrame.
import { startA2uiDemo } from "/a2ui/demo.js";

startA2uiDemo({
  mode: "3 · Open-ended",
  title: "Model-written HTML as a custom A2UI component",
  blurb:
    "The Basic Catalog cannot run model-written code, so this surface uses a custom catalog: Basic + HtmlFrame. The whole screen is one HtmlFrame whose HTML the model wrote, drawn in a sandboxed iframe.",
  examples: ["Plan 3 days in Tokyo", "An interactive packing checklist for a ski trip", "A budget slider for a week in Bali"],
});
