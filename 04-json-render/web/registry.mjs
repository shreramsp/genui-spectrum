// Part 04 - one React component per catalog entry (defineRegistry checks they match the catalog).
// Components get { props, children, emit }. emit("press") fires whatever action the element's
// "on" field binds to that event. No JSX, so this file also loads in Node for the checker.

import { defineRegistry } from "@json-render/react";
import { createElement as h, useEffect, useRef } from "react";

const BASE = {
  Card: ({ props, children }) =>
    h("section", { className: "c-card" }, h("h3", null, props.title), props.subtitle ? h("p", { className: "jr-muted" }, props.subtitle) : null, children),
  Row: ({ children }) => h("div", { className: "c-row" }, children),
  Text: ({ props }) => h("p", { className: `c-text jr-${props.tone ?? "normal"}` }, props.text),
  Metric: ({ props }) =>
    h("div", { className: "c-metric" },
      h("div", { className: "c-metric-label" }, props.label),
      h("div", { className: "c-metric-value" }, props.value),
      props.hint ? h("div", { className: "c-metric-hint" }, props.hint) : null),
  // Props may be {"$state": "/path"} that has not streamed in yet -> undefined: default arrays.
  Table: ({ props }) =>
    h("div", { className: "c-table-wrap" },
      h("table", { className: "c-table" },
        h("thead", null, h("tr", null, (props.columns ?? []).map((c, i) => h("th", { key: i }, c)))),
        h("tbody", null, (props.rows ?? []).map((r, i) => h("tr", { key: i }, r.map((cell, j) => h("td", { key: j }, String(cell)))))))),
  BarChart: ({ props }) => {
    const values = props.values ?? [];
    const max = Math.max(1, ...values);
    return h("figure", { className: "c-chart" },
      h("figcaption", null, props.title),
      (props.labels ?? []).map((label, i) =>
        h("div", { key: i, className: "c-bar-row" },
          h("span", { className: "c-bar-label" }, label),
          h("div", { className: "c-bar-track" }, h("div", { className: "c-bar", style: { width: `${((values[i] ?? 0) / max) * 100}%` } })),
          h("span", { className: "c-bar-value" }, String(values[i] ?? "")))));
  },
  Button: ({ props, emit }) => h("button", { type: "button", className: "c-button", onClick: () => emit("press") }, props.label),
};

// The escape hatch. Its sendAction() calls go to the page through a DOM event (see app.mjs),
// and from there through the same server allow-list as catalog actions.
function HtmlFrame({ props }) {
  const box = useRef(null);
  useEffect(() => {
    let cleanup = () => {};
    import("/shared/sandbox.js").then(({ mountSandbox }) => {
      if (!box.current) return;
      box.current.replaceChildren();
      cleanup = mountSandbox(box.current, props.html, {
        height: props.height ?? 360,
        allowedActions: props.actions ?? [],
        onAction: (name, payload) => window.dispatchEvent(new CustomEvent("jr-html-action", { detail: { name, payload } })),
      });
    });
    return () => cleanup();
  }, [props.html, (props.actions ?? []).join(",")]);
  return h("div", { className: "c-htmlframe" }, h("div", { className: "c-htmlframe-tag" }, "AI-generated region · sandboxed"), h("div", { ref: box }));
}

export function makeRegistry(catalog, { allowHtml = false } = {}) {
  return defineRegistry(catalog, { components: allowHtml ? { ...BASE, HtmlFrame } : BASE }).registry;
}
