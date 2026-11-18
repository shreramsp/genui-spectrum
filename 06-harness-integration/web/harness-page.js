// The page for all four harness demos. The agent's render tool decides what arrives in
// CUSTOM "render": {kind: "component" | "spec" | "html"}. Everything else in the event log
// (steps, file tool calls, their results) is the agent loop itself, live.

import { runAgent } from "/shared/agui-client.js";
import { renderSpec } from "/shared/render.js";
import { mountSandbox } from "/shared/sandbox.js";
import { createShell } from "/shared/shell.js";

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = String(text);
  return n;
};

// Static mode: the two pre-built views the agent can choose from.
const COMPONENTS = {
  show_budget({ title, items }) {
    const card = el("section", "c-card");
    const total = items.reduce((s, i) => s + i.amount, 0);
    const big = el("div", "c-metric");
    big.append(el("div", "c-metric-label", "Total"), el("div", "c-metric-value", `$${total.toLocaleString()}`));
    card.append(el("h3", null, title), big);
    const max = Math.max(1, ...items.map((i) => i.amount));
    for (const i of items) {
      const row = el("div", "c-bar-row");
      const track = el("div", "c-bar-track");
      const bar = el("div", "c-bar");
      bar.style.width = `${(i.amount / max) * 100}%`;
      track.appendChild(bar);
      row.append(el("span", "c-bar-label", i.category), track, el("span", "c-bar-value", i.amount));
      card.appendChild(row);
    }
    return card;
  },
  show_bookings({ rows }) {
    const card = el("section", "c-card");
    card.appendChild(el("h3", null, "Bookings"));
    const table = el("table", "c-table");
    const head = table.createTHead().insertRow();
    ["Date", "Type", "Name", "Price", "Status"].forEach((c) => head.appendChild(el("th", null, c)));
    const body = table.createTBody();
    rows.forEach((r) => {
      const tr = body.insertRow();
      [r.date, r.type, r.name, `$${r.price}`, r.status].forEach((v) => tr.appendChild(el("td", null, v)));
    });
    card.appendChild(table);
    return card;
  },
};

export function startHarnessDemo(config) {
  async function run(shell, text, forwardedProps = {}) {
    await runAgent("/agent", { text, forwardedProps }, (event) => {
      shell.logEvent(event);
      if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
      if (event.type === "RUN_ERROR") shell.error(event.message);
      if (event.type === "CUSTOM" && event.name === "render") draw(shell, event.value);
    });
  }

  function draw(shell, ui) {
    if (ui.kind === "component") shell.ui.replaceChildren(COMPONENTS[ui.name](ui.props));
    if (ui.kind === "spec") renderSpec(ui.spec, shell.ui, { onAction: (name, payload) => act(shell, name, payload) });
    if (ui.kind === "html") {
      const box = el("div", "c-htmlframe");
      box.appendChild(el("div", "c-htmlframe-tag", "AI-generated HTML · sandboxed"));
      shell.ui.replaceChildren(box);
      mountSandbox(box, ui.html, { height: 460 });
    }
  }

  async function act(shell, name, payload) {
    shell.setBusy(true);
    shell.resetLog();
    shell.say("");
    try {
      await run(shell, `[action] ${name}`, { action: name, payload });
    } finally {
      shell.setBusy(false);
    }
  }

  createShell({
    part: "06 · Harness",
    ...config,
    onSubmit: (text, shell) => {
      shell.clearUI();
      return run(shell, text);
    },
  });
}
