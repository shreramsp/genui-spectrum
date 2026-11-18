// The checker the Python server calls:
//   echo '{"jsonl": "...", "base": {...} | null, "allowHtml": false, "withActions": false}' | node dist/check.mjs
// It compiles the JSONL patches (onto `base`, if given) with json-render's own compiler,
// validates the spec with the catalog AND json-render's structural checks, and prints JSON:
//   {spec, errors: [...], types: [...], actions: [...], patches: n}
import { compileSpecStream, validateSpec } from "@json-render/core";
import { makeCatalog } from "./catalog.mjs";

let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  const { jsonl, base, allowHtml, withActions } = JSON.parse(input);
  const catalog = makeCatalog({ allowHtml, withActions });
  const spec = compileSpecStream(jsonl, base ?? { root: "", elements: {}, state: {} });
  const errors = [];

  const zod = catalog.validate(spec);
  if (!zod.success) for (const issue of zod.error.issues.slice(0, 8)) errors.push(`${issue.path.join("/")}: ${issue.message}`);
  for (const issue of validateSpec(spec).issues) if (issue.severity === "error") errors.push(issue.message);
  if (!spec.root || !spec.elements?.[spec.root]) errors.push("root must name an existing element");

  const types = [];
  const actions = new Set();
  const allowedActions = Object.keys(catalog.data.actions ?? {});
  for (const [id, el] of Object.entries(spec.elements ?? {})) {
    types.push(el.type);
    for (const binding of Object.values(el.on ?? {})) {
      for (const b of [binding].flat()) {
        if (!allowedActions.includes(b.action)) errors.push(`${id}: action "${b.action}" is not in the catalog`);
        else actions.add(b.action);
      }
    }
    for (const a of el.type === "HtmlFrame" ? el.props?.actions ?? [] : []) {
      if (!allowedActions.includes(a)) errors.push(`${id}: HtmlFrame action "${a}" is not in the catalog`);
      else actions.add(a);
    }
  }
  const patches = jsonl.split("\n").filter((l) => l.trim().startsWith("{")).length;
  process.stdout.write(JSON.stringify({ spec, errors, types, actions: [...actions], patches }));
});
