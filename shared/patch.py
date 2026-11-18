"""Minimal JSON Patch (RFC 6902) for UI specs: diff two specs, or apply operations.

AG-UI's STATE_DELTA carries JSON Patch. Instead of resending the whole UI after a
click, we send only what changed, e.g.
    [{"op": "replace", "path": "/ui/elements/costs", "value": {...}}]
"""

import copy


def _esc(key):
    return str(key).replace("~", "~0").replace("/", "~1")


def _unesc(part):
    return part.replace("~1", "/").replace("~0", "~")


def diff_spec(old, new, prefix="/ui"):
    """Element-level diff: one op per added, changed or removed element (+ root)."""
    ops = []
    if old.get("root") != new.get("root"):
        ops.append({"op": "replace", "path": f"{prefix}/root", "value": new["root"]})
    old_el, new_el = old.get("elements", {}), new.get("elements", {})
    for el_id, el in new_el.items():
        if el_id not in old_el:
            ops.append({"op": "add", "path": f"{prefix}/elements/{_esc(el_id)}", "value": el})
        elif old_el[el_id] != el:
            ops.append({"op": "replace", "path": f"{prefix}/elements/{_esc(el_id)}", "value": el})
    for el_id in old_el:
        if el_id not in new_el:
            ops.append({"op": "remove", "path": f"{prefix}/elements/{_esc(el_id)}"})
    return ops


def apply_patch(doc, ops):
    """Apply add / replace / remove operations to a copy of `doc` (objects only)."""
    doc = copy.deepcopy(doc)
    for op in ops:
        *parents, last = [_unesc(p) for p in op["path"].lstrip("/").split("/")]
        target = doc
        for part in parents:
            target = target[part]
        if op["op"] in ("add", "replace"):
            target[last] = op["value"]
        elif op["op"] == "remove":
            del target[last]
        else:
            raise ValueError(f"unsupported op {op['op']}")
    return doc
