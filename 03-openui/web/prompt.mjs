// Write the system prompts the catalog generates (run by `npm run build`):
//   prompt.txt       catalog only            (modes 1-2)
//   prompt_html.txt  catalog + HtmlArtifact  (mode 4)
// server code reads these files, so Python never needs to understand Zod.
import { writeFileSync } from "node:fs";
import { makeLibrary, PROMPT_OPTIONS } from "./library.mjs";

writeFileSync(new URL("./prompt.txt", import.meta.url), makeLibrary().prompt(PROMPT_OPTIONS));
writeFileSync(
  new URL("./prompt_html.txt", import.meta.url),
  makeLibrary({ allowHtml: true }).prompt({
    ...PROMPT_OPTIONS,
    additionalRules: [
      ...PROMPT_OPTIONS.additionalRules,
      "Use EXACTLY ONE HtmlArtifact, only for an interactive piece the other components cannot express. Escape quotes inside its document string.",
      "Add one Button with a snake_case action, e.g. cheaper.",
    ],
  }),
);
console.log("wrote prompt.txt and prompt_html.txt");
