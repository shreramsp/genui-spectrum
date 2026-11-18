"""A terminal renderer for flat element-map specs: the same spec, drawn as text instead of HTML.

Works for the shared catalog (Parts 01, 06) and json-render specs (Part 04), which share the
{root, elements: {id: {type, props, children}}} shape. Also resolves json-render's
{"$state": ...}, {"$item": ...}, {"$index": ...} and "repeat".
"""


def _get(doc, pointer):
    for part in [p for p in str(pointer).split("/") if p]:
        if isinstance(doc, list) and part.isdigit() and int(part) < len(doc):
            doc = doc[int(part)]
        elif isinstance(doc, dict):
            doc = doc.get(part)
        else:
            return None
    return doc


def _resolve(value, state, item, index):
    if isinstance(value, dict):
        if "$state" in value:
            return _get(state, value["$state"])
        if "$item" in value:
            return item.get(value["$item"]) if isinstance(item, dict) and value["$item"] else item
        if "$index" in value:
            return index
    if isinstance(value, list):
        return [_resolve(v, state, item, index) for v in value]
    return value


def render_terminal(spec, width=58):
    """Draw a spec as plain text. Handles $state, $item, $index and repeat."""
    elements, state = spec.get("elements", {}), spec.get("state", {})
    out = []

    def emit(text, depth):
        out.append(("│ " * depth) + text)

    def node(el_id, depth, item=None, index=None, seen=()):
        el = elements.get(el_id)
        if el is None or el_id in seen:
            return
        seen = seen + (el_id,)
        p = {k: _resolve(v, state, item, index) for k, v in (el.get("props") or {}).items()}
        kind = el.get("type")
        if kind == "Card":
            emit(f"┌─ {p.get('title') or ''}", depth)
            if p.get("subtitle"):
                emit(f"  {p['subtitle']}", depth + 1)
        elif kind == "Text":
            emit(str(p.get("text") or ""), depth)
        elif kind == "Metric":
            hint = f"  ({p['hint']})" if p.get("hint") else ""
            emit(f"{p.get('label')}: {p.get('value')}{hint}", depth)
        elif kind == "Table":
            cols, rows = p.get("columns") or [], p.get("rows") or []
            widths = [max([len(str(c))] + [len(str(r[i])) for r in rows if i < len(r)]) for i, c in enumerate(cols)]
            emit("  ".join(str(c).ljust(w) for c, w in zip(cols, widths)), depth)
            emit("  ".join("─" * w for w in widths), depth)
            for r in rows:
                emit("  ".join(str(c).ljust(w) for c, w in zip(r, widths)), depth)
        elif kind == "BarChart":
            labels, values = p.get("labels") or [], p.get("values") or []
            emit(str(p.get("title") or ""), depth)
            top = max(values or [1]) or 1
            pad = max([len(str(lab)) for lab in labels] or [0])
            for lab, v in zip(labels, values):
                emit(f"{str(lab).ljust(pad)} {'█' * max(1, round(24 * v / top))} {v}", depth)
        elif kind == "Button":
            emit(f"[ {p.get('label')} ]", depth)
        elif kind == "HtmlFrame":
            emit(f"[ sandboxed HTML, {len(p.get('html') or ''):,} chars: open the web page to run it ]", depth)
        elif kind != "Row":
            emit(f"<{kind}>", depth)

        inner = depth + 1 if kind == "Card" else depth
        repeat = el.get("repeat")
        if repeat:
            items = _get(state, repeat.get("statePath")) or []
            for i, it in enumerate(items):
                for child in el.get("children", []):
                    node(child, inner, it, i, seen)
        else:
            for child in el.get("children", []):
                node(child, inner, item, index, seen)
        if kind == "Card":
            emit("└" + "─" * 20, depth)

    node(spec.get("root"), 0)
    return "\n".join(out)
