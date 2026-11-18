// 01 AG-UI · 4 MIXED — catalog components + one sandboxed region; clicks round-trip to the agent.
//   typed request -> STATE_SNAPSHOT (whole UI)
//   a click       -> new run with forwardedProps.action -> STATE_DELTA (only what changed)

import { runAgent } from "/shared/agui-client.js";
import { applyPatch } from "/shared/patch.js";
import { renderSpec } from "/shared/render.js";
import { createShell } from "/shared/shell.js";

let state = {}; // AG-UI shared state: { ui: spec }

async function run(shell, text, forwardedProps = {}) {
  await runAgent("/agent", { text, state, forwardedProps }, (event) => {
    shell.logEvent(event);
    if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
    if (event.type === "STATE_SNAPSHOT") state = event.snapshot;
    if (event.type === "STATE_DELTA") state = applyPatch(state, event.delta);
    if (event.type === "STATE_SNAPSHOT" || event.type === "STATE_DELTA") draw(shell);
    if (event.type === "RUN_ERROR") shell.error(event.message);
  });
}

function draw(shell) {
  renderSpec(state.ui, shell.ui, {
    // Catalog Buttons AND sendAction() from inside the sandbox both arrive here.
    onAction: async (name, payload) => {
      shell.setBusy(true);
      shell.resetLog();
      shell.say("");
      try {
        await run(shell, `[action] ${name}`, { action: name, payload });
      } finally {
        shell.setBusy(false);
      }
    },
  });
}

createShell({
  part: "01 · AG-UI",
  mode: "4 · Mixed",
  title: "Catalog components + one custom region",
  blurb:
    "Most of the screen comes from the validated catalog. One HtmlFrame (pink border) is model-written HTML in a sandbox. Clicks in either go back to the agent, which checks them against an allow-list and replies with a small STATE_DELTA patch.",
  examples: ["Plan 3 days in Tokyo", "A 5-day Italy rail trip on a student budget", "Weekend hiking trip near Seattle"],
  onSubmit: (text, shell) => {
    state = {}; // a typed request starts a fresh screen
    return run(shell, text);
  },
});
