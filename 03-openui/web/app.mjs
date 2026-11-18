// Part 03 - the page for all four OpenUI demos (bundled by esbuild into dist/openui-app.js).
//
// The program text arrives in pieces through AG-UI CUSTOM "openui" events:
//   {delta}  append text        {reset}  start over        {patch}  merge changed statements
// After EVERY change, OpenUI's <Renderer> re-parses the whole text and draws what it can.
// References that are not defined yet simply stay empty, so the screen fills in top-down.

import { Renderer, mergeStatements } from "@openuidev/react-lang";
import { createElement as h } from "react";
import { createRoot } from "react-dom/client";
import { runAgent } from "/shared/agui-client.js";
import { createShell } from "/shared/shell.js";
import { makeLibrary } from "./library.mjs";

export function startOpenUiDemo({ allowHtml = false, ...config }) {
  const library = makeLibrary({ allowHtml });
  let program = "";
  let streaming = false;

  // Our own containers inside the shell's UI area: the rendered screen + the raw OpenUI Lang.
  const screen = document.createElement("div");
  const details = document.createElement("details");
  details.className = "ou-source";
  details.open = true;
  const summary = document.createElement("summary");
  const source = document.createElement("pre");
  details.append(summary, source);
  const root = createRoot(screen);

  let shell;
  let lastParse = null;
  const updateSummary = () => {
    const m = lastParse?.meta;
    summary.textContent = m
      ? `OpenUI Lang · ${m.statementCount} statements · ${m.unresolved.length} not yet defined${streaming ? " · streaming" : ""}`
      : "OpenUI Lang";
  };
  const draw = () => {
    root.render(
      h(Renderer, {
        response: program,
        library,
        isStreaming: streaming,
        onAction: (event) => {
          if (event.type === "trip_action") act(event.params.action, event.params.payload);
        },
        onParseResult: (r) => {
          lastParse = r;
          updateSummary();
        },
      }),
    );
    updateSummary();
    source.textContent = program || "(waiting for the model…)";
    source.scrollTop = source.scrollHeight;
  };

  async function run(text, forwardedProps = {}) {
    if (!screen.isConnected) shell.ui.replaceChildren(screen, details);
    await runAgent("/agent", { text, forwardedProps }, (event) => {
      shell.logEvent(event);
      if (event.type === "RUN_STARTED") streaming = true;
      if (event.type === "RUN_FINISHED" || event.type === "RUN_ERROR") streaming = false;
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "RUN_ERROR") shell.appendSay(`\nError: ${event.message}`);
      if (event.type === "CUSTOM" && event.name === "openui") {
        const v = event.value;
        if (v.reset) program = "";
        if (v.delta) program += v.delta;
        if (v.patch) program = mergeStatements(program, v.patch, "root");
      }
      draw();
    });
  }

  async function act(action, payload) {
    shell.setBusy(true);
    shell.resetLog();
    shell.say("");
    try {
      await run(`[action] ${action}`, { action, payload });
    } finally {
      shell.setBusy(false);
    }
  }

  shell = createShell({
    part: "03 · OpenUI",
    ...config,
    onSubmit: (text) => {
      program = ""; // a typed request starts a fresh screen
      return run(text);
    },
  });
  shell.ui.replaceChildren(screen, details);
  draw();
}
