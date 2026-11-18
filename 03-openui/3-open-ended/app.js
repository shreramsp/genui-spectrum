// 03 OpenUI · 3 OPEN-ENDED — the generic OpenUI page; the program is one HtmlArtifact.
import { startOpenUiDemo } from "/openui/dist/openui-app.js";

startOpenUiDemo({
  allowHtml: true,
  mode: "3 · Open-ended",
  title: "Raw HTML streamed inside an OpenUI HtmlArtifact",
  blurb:
    "The model writes raw HTML. The server streams it inside the string argument of one HtmlArtifact statement: you see the source grow while it streams, then it runs in a sandboxed iframe.",
  examples: ["Plan 3 days in Tokyo", "An interactive packing checklist for a ski trip", "A budget slider for a week in Bali"],
});
