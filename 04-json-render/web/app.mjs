// Part 04 - the page for all four json-render demos (bundled by esbuild into dist/jr-app.js).
//
// The spec arrives as JSONL JSON-Patch lines in AG-UI CUSTOM "jsonrender" events:
//   {line}  one patch, e.g. {"op":"add","path":"/elements/card-1","value":{...}}
//   {reset} start a new spec
//   {terminal} the same spec drawn by the Python terminal renderer (shown below the UI)
// json-render's createSpecStreamCompiler applies each patch; <Renderer> draws after every one.

import { createSpecStreamCompiler } from "@json-render/core";
import { JSONUIProvider, Renderer } from "@json-render/react";
import { createElement as h } from "react";
import { createRoot } from "react-dom/client";
import { runAgent } from "/shared/agui-client.js";
import { createShell } from "/shared/shell.js";
import { makeCatalog } from "./catalog.mjs";
import { makeRegistry } from "./registry.mjs";

export function startJsonRenderDemo({ allowHtml = false, withActions = false, ...config }) {
  const catalog = makeCatalog({ allowHtml, withActions });
  const registry = makeRegistry(catalog, { allowHtml });
  let compiler = createSpecStreamCompiler();
  let spec = null;
  let lines = [];
  let loading = false;
  let version = 0;

  const screen = document.createElement("div");
  const panes = document.createElement("div");
  panes.className = "jr-panes";
  const mk = (title) => {
    const d = document.createElement("details");
    d.className = "ou-source";
    d.open = true;
    const s = document.createElement("summary");
    s.textContent = title;
    const pre = document.createElement("pre");
    d.append(s, pre);
    panes.appendChild(d);
    return { summary: s, pre };
  };
  const patchPane = mk("JSONL patches");
  const termPane = mk("Same spec, terminal renderer (Python)");
  termPane.pre.classList.add("jr-terminal");
  const root = createRoot(screen);

  // Every catalog action becomes a handler that sends it back to the agent.
  const handlers = Object.fromEntries(Object.keys(catalog.data.actions ?? {}).map((name) => [name, (params) => act(name, params ?? {})]));
  window.addEventListener("jr-html-action", (e) => act(e.detail.name, e.detail.payload ?? {}));

  let shell;
  const draw = () => {
    version += 1;
    const state = { ...(spec?.state ?? {}) }; // a fresh object so the state provider sees updates
    root.render(
      spec && spec.root && spec.elements
        ? h(JSONUIProvider, { key: version, registry, initialState: state, handlers }, h(Renderer, { spec, registry, loading }))
        : h("p", { className: "shell-empty" }, "The generated UI appears here."),
    );
    patchPane.summary.textContent = `JSONL patches · ${lines.length} applied${loading ? " · streaming" : ""}`;
    patchPane.pre.textContent = lines.join("\n") || "(waiting…)";
    patchPane.pre.scrollTop = patchPane.pre.scrollHeight;
  };

  async function run(text, forwardedProps = {}) {
    if (!screen.isConnected) shell.ui.replaceChildren(screen, panes);
    await runAgent("/agent", { text, forwardedProps }, (event) => {
      shell.logEvent(event);
      if (event.type === "RUN_STARTED") loading = true;
      if (event.type === "RUN_FINISHED" || event.type === "RUN_ERROR") loading = false;
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "RUN_ERROR") shell.appendSay(`\nError: ${event.message}`);
      if (event.type === "CUSTOM" && event.name === "jsonrender") {
        const v = event.value;
        if (v.reset) {
          compiler = createSpecStreamCompiler();
          spec = null;
          lines = [];
          termPane.pre.textContent = "";
        }
        if (v.line) {
          lines.push(v.line);
          spec = compiler.push(v.line + "\n").result;
        }
        if (v.terminal) termPane.pre.textContent = v.terminal;
      }
      draw();
    });
  }

  async function act(name, params) {
    shell.setBusy(true);
    shell.resetLog();
    shell.say("");
    try {
      await run(`[action] ${name}`, { action: name, params });
    } finally {
      shell.setBusy(false);
    }
  }

  shell = createShell({
    part: "04 · json-render",
    ...config,
    onSubmit: (text) => run(text),
  });
  shell.ui.replaceChildren(screen, panes);
  draw();
}
