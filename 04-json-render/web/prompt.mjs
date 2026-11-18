// Write the system prompts the catalog generates (run by `npm run build`):
//   prompt.txt        catalog only                         (mode 2)
//   prompt_mixed.txt  catalog + HtmlFrame + actions        (mode 4)
// Each includes json-render's own instructions for streaming JSONL patches.
import { writeFileSync } from "node:fs";
import { makeCatalog, RULES } from "./catalog.mjs";

const write = (file, catalog, extra = []) =>
  writeFileSync(new URL(file, import.meta.url), catalog.prompt({ system: "You turn a trip request into a UI spec.", customRules: [...RULES, ...extra] }));

write("./prompt.txt", makeCatalog());
write("./prompt_mixed.txt", makeCatalog({ allowHtml: true, withActions: true }), [
  "Use EXACTLY ONE HtmlFrame, only for an interactive piece the other components cannot express (e.g. a pace slider). List its sendAction names in actions; use set_pace with {pace}.",
  'Include one Button bound to the cheaper action: "on": {"press": {"action": "cheaper", "params": {}}}.',
  "Do not use $state, repeat or visible in this mode; put values directly in props.",
]);
console.log("wrote prompt.txt and prompt_mixed.txt");
