// 01 AG-UI · 2 DECLARATIVE — the page renders whatever spec arrives in shared state.
// No trip-specific code here at all: the generic catalog renderer draws the model's layout.

import { runAgent } from "/shared/agui-client.js";
import { renderSpec } from "/shared/render.js";
import { createShell } from "/shared/shell.js";

let state = {}; // the AG-UI shared state, kept in sync by STATE_SNAPSHOT events

createShell({
  part: "01 · AG-UI",
  mode: "2 · Declarative",
  title: "The agent arranges catalog components",
  blurb:
    "The model writes a JSON spec using only approved components. The server validates it, then sends it as shared state (STATE_SNAPSHOT). The page renders state.ui with one generic renderer.",
  examples: ["Plan 3 days in Tokyo", "Compare Lisbon and Barcelona for a cheap 4-day trip", "Weekend in New York with kids"],

  async onSubmit(text, shell) {
    await runAgent("/agent", { text, state }, (event) => {
      shell.logEvent(event);
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "STATE_SNAPSHOT") {
        state = event.snapshot;
        renderSpec(state.ui, shell.ui, {
          onAction: (name) => shell.say(`Button action "${name}" clicked. Actions round-trip to the agent in 4-mixed.`),
        });
      }
      if (event.type === "RUN_ERROR") shell.error(event.message);
    });
  },
});
