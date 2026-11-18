// Part 03 - the OpenUI catalog: Zod props + a React renderer per component.
//
// defineComponent() does three jobs at once (like shared/catalog.py, but with the real library):
//   1. prompt     library.prompt() turns each Zod schema into a signature line for the model
//   2. validator  createParser(library.toJSONSchema()) checks the model's program
//   3. renderer   <Renderer library={...}> draws each statement with its component
//
// OpenUI Lang is positional: `m1 = Metric("Budget", "$735")`. The KEY ORDER of each
// z.object() is the argument order. No JSX here, so this file runs in Node and the browser.

import { createLibrary, defineComponent, useIsStreaming, useTriggerAction } from "@openuidev/react-lang";
import { createElement as h, useEffect, useRef } from "react";
import { z } from "zod";

const Stack = defineComponent({
  name: "Stack",
  description: "Lays children out in a column (default) or a row",
  props: z.object({
    children: z.array(z.any()).describe("child components"),
    direction: z.enum(["column", "row"]).optional(),
  }),
  component: ({ props, renderNode }) => h("div", { className: `ou-stack ou-${props.direction ?? "column"}` }, renderNode(props.children)),
});

const Card = defineComponent({
  name: "Card",
  description: "A titled box that groups children",
  props: z.object({ title: z.string(), children: z.array(z.any()).describe("child components") }),
  component: ({ props, renderNode }) => h("section", { className: "c-card" }, h("h3", null, props.title), renderNode(props.children)),
});

const Text = defineComponent({
  name: "Text",
  description: "A paragraph, or a heading with size heading",
  props: z.object({ text: z.string(), size: z.enum(["small", "body", "heading"]).optional() }),
  component: ({ props }) => h(props.size === "heading" ? "h2" : "p", { className: `ou-text ou-${props.size ?? "body"}` }, props.text),
});

const Metric = defineComponent({
  name: "Metric",
  description: "One big number with a label",
  props: z.object({ label: z.string(), value: z.union([z.string(), z.number()]), hint: z.string().optional() }),
  component: ({ props }) =>
    h("div", { className: "c-metric" },
      h("div", { className: "c-metric-label" }, props.label),
      h("div", { className: "c-metric-value" }, String(props.value)),
      props.hint ? h("div", { className: "c-metric-hint" }, props.hint) : null),
});

const Table = defineComponent({
  name: "Table",
  description: "A table with column headers and rows of cells",
  props: z.object({ columns: z.array(z.string()), rows: z.array(z.array(z.union([z.string(), z.number()]))) }),
  component: ({ props }) =>
    h("div", { className: "c-table-wrap" },
      h("table", { className: "c-table" },
        h("thead", null, h("tr", null, props.columns.map((c, i) => h("th", { key: i }, c)))),
        h("tbody", null, props.rows.map((row, i) => h("tr", { key: i }, row.map((cell, j) => h("td", { key: j }, String(cell)))))))),
});

const BarChart = defineComponent({
  name: "BarChart",
  description: "Horizontal bars; labels and values have equal length",
  props: z.object({ title: z.string(), labels: z.array(z.string()), values: z.array(z.number()) }),
  component: ({ props }) => {
    const max = Math.max(1, ...props.values);
    return h("figure", { className: "c-chart" },
      h("figcaption", null, props.title),
      props.values.map((v, i) =>
        h("div", { key: i, className: "c-bar-row" },
          h("span", { className: "c-bar-label" }, props.labels[i] ?? ""),
          h("div", { className: "c-bar-track" }, h("div", { className: "c-bar", style: { width: `${(v / max) * 100}%` } })),
          h("span", { className: "c-bar-value" }, String(v)))));
  },
});

// A Button fires an OpenUI action. The page's <Renderer onAction> receives it.
function ButtonRenderer({ props }) {
  const trigger = useTriggerAction();
  return h("button", {
    type: "button",
    className: "c-button",
    onClick: () => trigger(props.label, undefined, { type: "trip_action", params: { action: props.action } }),
  }, props.label);
}
const Button = defineComponent({
  name: "Button",
  description: "A button; clicking sends `action` (snake_case) back to the agent",
  props: z.object({ label: z.string(), action: z.string() }),
  component: ButtonRenderer,
});

// The open-ended escape hatch (OpenUI's own pattern is also called HtmlArtifact).
// While the program is still streaming we show the raw source; once complete it runs in our sandbox.
function HtmlArtifactRenderer({ props }) {
  const streaming = useIsStreaming();
  const trigger = useTriggerAction();
  const box = useRef(null);
  useEffect(() => {
    if (streaming || !box.current) return undefined;
    let cleanup = () => {};
    // Loaded lazily: the sandbox only exists in the browser (Node uses this file for prompts/checks).
    import("/shared/sandbox.js").then(({ mountSandbox }) => {
      if (!box.current) return;
      box.current.replaceChildren();
      cleanup = mountSandbox(box.current, props.document, {
        height: 380,
        allowedActions: props.actions ?? [],
        onAction: (name, payload) => trigger(`[html] ${name}`, undefined, { type: "trip_action", params: { action: name, payload } }),
      });
    });
    return () => cleanup();
  }, [streaming, props.document, (props.actions ?? []).join(",")]);
  return h("div", { className: "c-htmlframe" },
    h("div", { className: "c-htmlframe-tag" }, `${props.title} · AI-generated HTML · ${streaming ? "streaming…" : "sandboxed"}`),
    streaming ? h("pre", { className: "ou-raw" }, props.document.slice(-1200)) : h("div", { ref: box }));
}
const HtmlArtifact = defineComponent({
  name: "HtmlArtifact",
  description:
    "Custom HTML/CSS/JS for something the other components cannot express. Inline everything, no external URLs. Inside, call sendAction('name') for each name in actions.",
  props: z.object({
    title: z.string(),
    document: z.string().describe("an HTML fragment with inline <style> and <script>"),
    actions: z.array(z.string()).optional().describe("action names the HTML may send"),
  }),
  component: HtmlArtifactRenderer,
});

const CATALOG = [Stack, Card, Text, Metric, Table, BarChart, Button];

export function makeLibrary({ allowHtml = false } = {}) {
  return createLibrary({ components: allowHtml ? [...CATALOG, HtmlArtifact] : CATALOG, root: "Stack" });
}

export const PROMPT_OPTIONS = {
  preamble: "You design screens for a trip-planning app. Answer with OpenUI Lang only: no prose, no code fences.",
  additionalRules: [
    "The first statement is root = Stack([...]).",
    "Put numbers in Metric values and BarChart values, not in Text.",
    "Keep every string on one line. Use realistic example data; budgets are rough estimates in USD.",
  ],
};
