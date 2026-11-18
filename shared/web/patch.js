// Apply JSON Patch (RFC 6902) add / replace / remove to a copy of a document.
// Used for AG-UI STATE_DELTA events. Mirrors shared/patch.py.

export function applyPatch(doc, ops) {
  const out = structuredClone(doc);
  for (const op of ops) {
    const parts = op.path.replace(/^\//, "").split("/").map((p) => p.replace(/~1/g, "/").replace(/~0/g, "~"));
    const last = parts.pop();
    let target = out;
    for (const p of parts) target = target[p];
    if (op.op === "add" || op.op === "replace") target[last] = op.value;
    else if (op.op === "remove") delete target[last];
    else throw new Error(`unsupported op ${op.op}`);
  }
  return out;
}
