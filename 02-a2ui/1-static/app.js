// 02 A2UI · 1 STATIC — the page is the generic A2UI client (../web/demo.js); only server.py differs.
import { startA2uiDemo } from "/a2ui/demo.js";

startA2uiDemo({
  mode: "1 · Static",
  title: "A fixed A2UI screen; the model fills in only the data",
  blurb:
    "The components (structure) are hand-written and arrive instantly. The model only writes the data model, which the components show through bindings like {path: \"/trip/title\"}. Re-plan sends an A2UI action; the reply is just a new updateDataModel.",
  examples: ["Plan 3 days in Tokyo", "Plan a long weekend in Rome", "4 days in Iceland in winter"],
});
