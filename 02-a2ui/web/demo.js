// The page for all four A2UI demos. It is the SAME in every mode: an A2UI renderer does not
// care whether a human, a template or a model wrote the messages. Only server.py changes.
//
//   AG-UI CUSTOM "a2ui" event  ->  client.process(message)
//   Button / sendAction click  ->  new AG-UI run with forwardedProps.a2uiAction = A2UI action message

import { runAgent } from "/shared/agui-client.js";
import { createShell } from "/shared/shell.js";
import { A2uiClient } from "/a2ui/a2ui.js";

export function startA2uiDemo(config) {
  let client;

  async function run(shell, text, forwardedProps = {}) {
    await runAgent("/agent", { text, forwardedProps }, (event) => {
      shell.logEvent(event);
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "CUSTOM" && event.name === "a2ui") client.process(event.value);
      if (event.type === "RUN_ERROR") shell.error(event.message);
    });
  }

  const shell = createShell({
    part: "02 · A2UI",
    ...config,
    onSubmit: (text, shell) => {
      client.reset(); // a typed request starts a fresh screen
      return run(shell, text);
    },
  });

  client = new A2uiClient(shell.ui, {
    onAction: async (action) => {
      shell.setBusy(true);
      shell.resetLog();
      shell.say("");
      try {
        await run(shell, `[action] ${action.name}`, { a2uiAction: action });
      } finally {
        shell.setBusy(false);
      }
    },
  });
}
