// 03 OpenUI · 1 STATIC — the generic OpenUI page (../web/app.mjs, bundled); only server.py differs.
import { startOpenUiDemo } from "/openui/dist/openui-app.js";

startOpenUiDemo({
  mode: "1 · Static",
  title: "A hand-written OpenUI Lang screen, filled with the model's data",
  blurb:
    "The screen is a developer-written OpenUI Lang template (screen.oui). The model only calls show_trip(...) with data; the server fills the template and streams it line by line. The source panel shows the program.",
  examples: ["Plan 3 days in Tokyo", "Plan a long weekend in Rome", "4 days in Iceland in winter"],
});
