// 02 A2UI · 2 DECLARATIVE — same generic A2UI page as every mode; the model wrote the components.
import { startA2uiDemo } from "/a2ui/demo.js";

startA2uiDemo({
  mode: "2 · Declarative",
  title: "The model writes the A2UI components and data",
  blurb:
    "The model designs the screen from the A2UI Basic Catalog. Each component is checked against the official v0.9.1 JSON Schema. Tick a checkbox, then press the button: the action carries values read from the data model at click time.",
  examples: ["Plan 3 days in Tokyo", "A packing planner for a ski trip", "Compare two hotels in Paris"],
});
