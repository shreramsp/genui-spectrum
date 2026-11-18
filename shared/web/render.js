// The renderer: one drawing function per catalog component (see shared/catalog.py).
// renderSpec() walks the flat element map from `root` and builds real DOM nodes.
// Anything not in this registry is never drawn - the model cannot invent new components.

import { mountSandbox } from "./sandbox.js";

const h = (tag, cls, text) => {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text != null) el.textContent = String(text); // textContent, never innerHTML: no injection
  return el;
};

export const REGISTRY = {
  Card: (p) => {
    const el = h("section", "c-card");
    if (p.title) el.appendChild(h("h3", null, p.title));
    return el;
  },
  Row: () => h("div", "c-row"),
  Text: (p) => h("p", "c-text", p.text),
  Metric: (p) => {
    const el = h("div", "c-metric");
    el.append(h("div", "c-metric-label", p.label), h("div", "c-metric-value", p.value));
    if (p.hint) el.appendChild(h("div", "c-metric-hint", p.hint));
    return el;
  },
  Table: (p) => {
    const table = h("table", "c-table");
    const head = table.createTHead().insertRow();
    p.columns.forEach((c) => head.appendChild(h("th", null, c)));
    const body = table.createTBody();
    p.rows.forEach((r) => {
      const tr = body.insertRow();
      r.forEach((cell) => tr.appendChild(h("td", null, cell)));
    });
    const wrap = h("div", "c-table-wrap");
    wrap.appendChild(table);
    return wrap;
  },
  BarChart: (p) => {
    const el = h("figure", "c-chart");
    el.appendChild(h("figcaption", null, p.title));
    const max = Math.max(...p.values, 1);
    p.labels.forEach((label, i) => {
      const row = h("div", "c-bar-row");
      const bar = h("div", "c-bar");
      bar.style.width = `${(p.values[i] / max) * 100}%`;
      const track = h("div", "c-bar-track");
      track.appendChild(bar);
      row.append(h("span", "c-bar-label", label), track, h("span", "c-bar-value", p.values[i]));
      el.appendChild(row);
    });
    return el;
  },
  Button: (p, ctx) => {
    const el = h("button", "c-button", p.label);
    el.type = "button";
    el.onclick = () => ctx.onAction?.(p.action, null);
    return el;
  },
  HtmlFrame: (p, ctx) => {
    const el = h("div", "c-htmlframe");
    el.appendChild(h("div", "c-htmlframe-tag", "AI-generated region · sandboxed"));
    mountSandbox(el, p.html, { height: Math.max(p.height || 360, 260), allowedActions: p.actions || [], onAction: ctx.onAction });
    return el;
  },
};

export function renderSpec(spec, container, ctx = {}) {
  container.replaceChildren();
  const seen = new Set();
  const build = (id) => {
    const el = spec.elements[id];
    if (!el || seen.has(id)) return null; // skip missing ids and cycles
    seen.add(id);
    const draw = REGISTRY[el.type];
    if (!draw) return h("div", "c-error", `Unknown component: ${el.type}`);
    const node = draw(el.props || {}, ctx);
    (el.children || []).forEach((childId) => {
      const child = build(childId);
      if (child) node.appendChild(child);
    });
    return node;
  };
  const root = build(spec.root);
  if (root) container.appendChild(root);
}
