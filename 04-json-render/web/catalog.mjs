// Part 04 - the json-render catalog: components (Zod props) AND the actions the UI may fire.
//
// One catalog, three jobs (the same idea as Parts 01-03, done by the json-render library):
//   catalog.prompt()    the system prompt, incl. json-render's JSONL patch format   (prompt.mjs)
//   catalog.validate()  checks a finished spec's types and props                     (check.mjs)
//   defineRegistry()    one React component per catalog entry                        (registry.mjs)
//
// New here: ACTIONS live in the catalog too. A Button binds its "press" event to one of them:
//   "on": {"press": {"action": "cheaper", "params": {}}}
// so the list of allowed actions is part of the contract the model is given.

import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const COMPONENTS = {
  Card: { props: z.object({ title: z.string(), subtitle: z.string().nullable() }), description: "A titled box. Put related elements inside it." },
  Row: { props: z.object({}), description: "Lays its children out side by side." },
  Text: { props: z.object({ text: z.string(), tone: z.enum(["normal", "muted", "strong"]).nullable() }), description: "One paragraph of text." },
  Metric: { props: z.object({ label: z.string(), value: z.string(), hint: z.string().nullable() }), description: "One key number with a label." },
  Table: { props: z.object({ columns: z.array(z.string()), rows: z.array(z.array(z.string())) }), description: "A table. Every row has one cell per column." },
  BarChart: {
    props: z.object({ title: z.string(), labels: z.array(z.string()), values: z.array(z.number()) }),
    description: "Horizontal bars. labels and values have the same length.",
  },
  Button: { props: z.object({ label: z.string() }), description: "A button. Bind its press event to an action with the on field." },
};

const HTML_FRAME = {
  HtmlFrame: {
    props: z.object({ html: z.string(), height: z.number().nullable(), actions: z.array(z.string()).nullable() }),
    description:
      "Custom HTML/CSS/JS in a sandbox, for something the other components cannot express. Inline everything, no external URLs. Inside, call sendAction('name', {...}) for each name in actions.",
  },
};

const ACTIONS = {
  cheaper: { params: z.object({}), description: "Ask the agent to make the trip cheaper. It answers with patches." },
  set_pace: { params: z.object({ pace: z.string() }), description: "Ask the agent to re-plan at a pace: relaxed, balanced or packed." },
};

export function makeCatalog({ allowHtml = false, withActions = false } = {}) {
  return defineCatalog(schema, {
    components: allowHtml ? { ...COMPONENTS, ...HTML_FRAME } : COMPONENTS,
    actions: withActions ? ACTIONS : {},
  });
}

export const RULES = [
  "You design screens for a trip-planning app. Use realistic example data; budgets are rough estimates in USD.",
  "Use short element ids such as card-1, row-1, metric-1.",
  "Every element needs type, props and children (an empty array when it has none). Use null for optional props you do not need.",
];
