"""Python side of Part 04: json-render specs, JSONL patch streaming, and a TERMINAL renderer.

json-render (Vercel Labs, @json-render/core + @json-render/react) describes a UI as a spec:
    {"root": "card-1", "elements": {"card-1": {"type": "Card", "props": {...}, "children": [...]}}, "state": {...}}
and the model builds it as a stream of JSONL lines, each one RFC 6902 JSON Patch:
    {"op":"add","path":"/root","value":"card-1"}
    {"op":"add","path":"/elements/card-1","value":{"type":"Card","props":{"title":"Tokyo"},"children":[]}}
Props can read the state model: {"$state": "/trip/title"}; an element with "repeat" renders its
children once per item of a state array, reading fields with {"$item": "plan"}.

The catalog and validator are JavaScript (web/catalog.mjs); the server calls web/dist/check.mjs.
The terminal renderer below is pure Python: the SAME spec drawn as text, a second "target".
"""

import json
import subprocess
from pathlib import Path

from shared.agui import custom

WEB = Path(__file__).resolve().parent / "web"
PROMPT = (WEB / "prompt.txt").read_text()
PROMPT_MIXED = (WEB / "prompt_mixed.txt").read_text()


def check(jsonl, base=None, allow_html=False, with_actions=False):
    """Compile JSONL patches (onto `base`) with json-render and validate against the catalog.

    Returns {spec, errors, types, actions, patches}.
    """
    payload = json.dumps({"jsonl": jsonl, "base": base, "allowHtml": allow_html, "withActions": with_actions})
    out = subprocess.run(["node", str(WEB / "dist" / "check.mjs")], input=payload, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"json-render checker failed: {out.stderr[-500:]}")
    return json.loads(out.stdout)


# ---------- AG-UI events the page understands (web/app.mjs) ----------


def line(patch):
    return custom("jsonrender", {"line": patch if isinstance(patch, str) else json.dumps(patch, ensure_ascii=False)})


def reset():
    return custom("jsonrender", {"reset": True})


def terminal(spec):
    return custom("jsonrender", {"terminal": render_terminal(spec)})


def spec_to_patches(spec):
    """A finished spec as the patch lines json-render would stream: root, each element, then state."""
    patches = [{"op": "add", "path": "/root", "value": spec["root"]}]
    patches += [{"op": "add", "path": f"/elements/{k}", "value": v} for k, v in spec["elements"].items()]
    patches += [{"op": "add", "path": f"/state/{k}", "value": v} for k, v in spec.get("state", {}).items()]
    return patches


def stream_patches(messages, fake):
    """Generator: forward each complete JSONL patch line as soon as the model finishes it; RETURN all lines.

    Lines that are not JSON patch objects (code fences, prose) are dropped.
    """
    from shared import llm

    buffer, kept = "", []

    def accept(text):
        text = text.strip()
        if not text.startswith("{"):
            return None
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None
        return text if isinstance(obj, dict) and "op" in obj and "path" in obj else None

    for chunk in llm.stream(messages, fake=fake):
        buffer += chunk
        while "\n" in buffer:
            raw, buffer = buffer.split("\n", 1)
            ok = accept(raw)
            if ok:
                kept.append(ok)
                yield line(ok)
    ok = accept(buffer)
    if ok:
        kept.append(ok)
        yield line(ok)
    return "\n".join(kept)


def action_from(run_input):
    props = run_input.forwarded_props or {}
    return props.get("action"), props.get("params") or {}


# ---------- the terminal renderer: same spec, different target ----------


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


if __name__ == "__main__":
    # python 04-json-render/jr_tools.py some_spec.json   -> draw any spec in the terminal
    import sys

    print(render_terminal(json.loads(Path(sys.argv[1]).read_text())))
