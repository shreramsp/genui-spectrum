"""Python side of Part 04: json-render specs, JSONL patch streaming, and a TERMINAL renderer.

json-render (Vercel Labs, @json-render/core + @json-render/react) describes a UI as a spec:
    {"root": "card-1", "elements": {"card-1": {"type": "Card", "props": {...}, "children": [...]}}, "state": {...}}
and the model builds it as a stream of JSONL lines, each one RFC 6902 JSON Patch:
    {"op":"add","path":"/root","value":"card-1"}
    {"op":"add","path":"/elements/card-1","value":{"type":"Card","props":{"title":"Tokyo"},"children":[]}}
Props can read the state model: {"$state": "/trip/title"}; an element with "repeat" renders its
children once per item of a state array, reading fields with {"$item": "plan"}.

The catalog and validator are JavaScript (web/catalog.mjs); the server calls web/dist/check.mjs.
The terminal renderer (shared/terminal.py) is pure Python: the SAME spec drawn as text, a second "target".
"""

import json
import subprocess
from pathlib import Path

from shared.agui import custom
from shared.terminal import render_terminal  # the same spec drawn as text (a second target)

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


if __name__ == "__main__":
    # python 04-json-render/jr_tools.py some_spec.json   -> draw any spec in the terminal
    import sys

    print(render_terminal(json.loads(Path(sys.argv[1]).read_text())))
