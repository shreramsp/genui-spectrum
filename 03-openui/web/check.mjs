// The checker the Python server calls:  echo '{"program": "...", "allowHtml": false}' | node dist/check.mjs
// It parses the OpenUI Lang program with the SAME library the page renders with, and prints JSON:
//   {errors: [...], components: [...], actions: [...], statementCount}
// With "patch" it first merges changed statements into "program" (OpenUI's mergeStatements).
import { createParser, mergeStatements } from "@openuidev/react-lang";
import { makeLibrary } from "./library.mjs";

let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  const { program: base, patch, allowHtml } = JSON.parse(input);
  const program = patch ? mergeStatements(base, patch, "root") : base;
  const parser = createParser(makeLibrary({ allowHtml }).toJSONSchema(), "Stack");
  const result = parser.parse(program);
  const errors = [];
  if (!result.root) errors.push("no root statement: start with root = Stack([...])");
  for (const e of result.meta.errors) errors.push(`${e.statementId ?? e.component}: ${e.message ?? e.code} ${e.path ?? ""}`.trim());
  for (const name of result.meta.unresolved) errors.push(`"${name}" is used but never defined`);

  // Walk the tree: which components were used, and which actions does the screen offer?
  const components = [];
  const actions = new Set();
  const walk = (node) => {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== "object") return;
    if (node.type === "element") {
      components.push(node.typeName);
      if (node.typeName === "Button" && node.props.action) actions.add(node.props.action);
      if (node.typeName === "HtmlArtifact") (node.props.actions ?? []).forEach((a) => actions.add(a));
      Object.values(node.props).forEach(walk);
    }
  };
  walk(result.root);
  process.stdout.write(JSON.stringify({ program, errors, components, actions: [...actions], statementCount: result.meta.statementCount }));
});
