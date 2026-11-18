// 01 AG-UI · 1 STATIC — the page owns three hand-written components.
// AG-UI TOOL_CALL events tell us WHICH one to draw; the streamed ARGS are its data.

import { runAgent } from "/shared/agui-client.js";
import { createShell } from "/shared/shell.js";

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = String(text);
  return n;
};

// ---- the pre-built components (written by a developer, not the model) ----
const COMPONENTS = {
  show_itinerary({ city, days = [] }) {
    const card = el("section", "c-card");
    card.appendChild(el("h3", null, `🗓  ${days.length}-day itinerary · ${city}`));
    days.forEach((d) => {
      const block = el("div", "c-metric");
      block.appendChild(el("strong", null, `Day ${d.day}: ${d.title}`));
      const ul = el("ul");
      (d.activities || []).forEach((a) => ul.appendChild(el("li", null, a)));
      block.appendChild(ul);
      card.appendChild(block);
    });
    return card;
  },

  show_budget({ city, currency = "USD", items = [] }) {
    const card = el("section", "c-card");
    const total = items.reduce((sum, i) => sum + Number(i.amount || 0), 0);
    card.appendChild(el("h3", null, `💰 Budget · ${city}`));
    const big = el("div", "c-metric");
    big.append(el("div", "c-metric-label", "Estimated total"), el("div", "c-metric-value", `${total.toLocaleString()} ${currency}`));
    card.appendChild(big);
    const max = Math.max(...items.map((i) => i.amount), 1);
    items.forEach((i) => {
      const row = el("div", "c-bar-row");
      const track = el("div", "c-bar-track");
      const bar = el("div", "c-bar");
      bar.style.width = `${(i.amount / max) * 100}%`;
      track.appendChild(bar);
      row.append(el("span", "c-bar-label", i.category), track, el("span", "c-bar-value", i.amount));
      card.appendChild(row);
    });
    return card;
  },

  show_packing_list({ city, items = [] }) {
    const card = el("section", "c-card");
    card.appendChild(el("h3", null, `🎒 Packing list · ${city}`));
    items.forEach((item) => {
      const label = el("label");
      const box = el("input");
      box.type = "checkbox";
      label.append(box, ` ${item}`);
      card.appendChild(label);
    });
    return card;
  },
};

createShell({
  part: "01 · AG-UI",
  mode: "1 · Static",
  title: "The agent picks a pre-built component",
  blurb:
    "Three components already exist in this page. The model sees them as tools. A TOOL_CALL event says which one to draw; its streamed arguments are the data.",
  examples: ["Plan 3 days in Tokyo", "What should I pack for Iceland in winter?", "Budget for a weekend in Paris"],

  async onSubmit(text, shell) {
    shell.clearUI();
    const pending = {}; // toolCallId -> { name, args: "" }

    await runAgent("/agent", { text }, (event) => {
      shell.logEvent(event);
      switch (event.type) {
        case "TEXT_MESSAGE_CONTENT":
          shell.appendSay(event.delta);
          break;
        case "TOOL_CALL_START":
          pending[event.toolCallId] = { name: event.toolCallName, args: "" };
          break;
        case "TOOL_CALL_ARGS":
          pending[event.toolCallId].args += event.delta; // JSON arrives in pieces
          break;
        case "TOOL_CALL_END": {
          const { name, args } = pending[event.toolCallId];
          const draw = COMPONENTS[name];
          if (draw) shell.ui.appendChild(draw(JSON.parse(args)));
          break;
        }
        case "RUN_ERROR":
          shell.error(event.message);
          break;
      }
    });
  },
});
