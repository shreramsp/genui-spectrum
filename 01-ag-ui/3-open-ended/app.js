// 01 AG-UI · 3 OPEN-ENDED — the model's HTML arrives in a CUSTOM event and runs in a sandbox.

import { runAgent } from "/shared/agui-client.js";
import { mountSandbox } from "/shared/sandbox.js";
import { createShell } from "/shared/shell.js";

createShell({
  part: "01 · AG-UI",
  mode: "3 · Open-ended",
  title: "The agent writes its own HTML",
  blurb:
    "No catalog: the model writes HTML, CSS and JavaScript. It arrives as an AG-UI CUSTOM event and runs inside a sandboxed iframe with no network and no access to this page.",
  examples: ["Plan 3 days in Tokyo", "An interactive packing checklist for a ski trip", "A budget slider for a week in Bali"],

  async onSubmit(text, shell) {
    shell.clearUI();
    await runAgent("/agent", { text }, (event) => {
      shell.logEvent(event);
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "CUSTOM" && event.name === "html_ui") {
        const box = document.createElement("div");
        box.className = "c-htmlframe";
        box.innerHTML = '<div class="c-htmlframe-tag">AI-generated HTML · sandboxed</div>';
        shell.ui.replaceChildren(box);
        mountSandbox(box, event.value.html, { height: 480 });
      }
      if (event.type === "RUN_ERROR") shell.error(event.message);
    });
  },
});
