"""04 json-render · 1 STATIC — a developer-written spec; the model only fills the STATE.

json-render separates elements from a "state" model. spec.json is written by hand: its props
read state with {"$state": "/trip/title"}, and the "Day by day" card has
"repeat": {"statePath": "/trip/days"}, so its child is drawn once per day.

The model only writes trip data. The server streams the whole thing as JSONL patches, the
way json-render expects:  /root -> each element -> /state/trip -> /state/trip/days/0, /1, ...
so the page shows the skeleton first and the days appear one by one.

Run:  python 04-json-render/1-static/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

import jr_tools as jr  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message  # noqa: E402
from shared.correct import ask_until_valid  # noqa: E402

SPEC = json.loads((HERE / "spec.json").read_text())  # written by the developer

DATA_SCHEMA = {
    "type": "object",
    "required": ["title", "summary", "days", "budget"],
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "days": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "budget": {
            "type": "array",
            "items": {"type": "object", "required": ["category", "amount"], "properties": {"category": {"type": "string"}, "amount": {"type": "number"}}},
        },
    },
}
VALIDATOR = Draft202012Validator(DATA_SCHEMA)

SYSTEM = """You fill in DATA for a fixed trip screen. Reply with ONLY a JSON object:
{"title": str, "summary": str (one sentence), "days": ["Day 1 · <a> · <b> · <c>", ...],
 "budget": [{"category": str, "amount": number}]}
Use realistic example data. Amounts are rough USD estimates, excluding flights."""

OFFLINE_REPLY = (HERE / "offline_reply.json").read_text()

app = create_app(HERE, mounts={"/jr": HERE.parent / "web"})


def to_patches(data):
    """Developer elements first, then state: scalars, then one patch per day (progressive)."""
    trip = {
        "title": data["title"],
        "summary": data["summary"],
        "dayCount": str(len(data["days"])),
        "total": f"${sum(b['amount'] for b in data['budget']):,.0f}",
        "labels": [b["category"] for b in data["budget"]],
        "values": [b["amount"] for b in data["budget"]],
        "days": [],
    }
    patches = jr.spec_to_patches({"root": SPEC["root"], "elements": SPEC["elements"]})
    patches.append({"op": "add", "path": "/state/trip", "value": trip})
    patches += [{"op": "add", "path": f"/state/trip/days/{i}", "value": {"day": i + 1, "plan": plan}} for i, plan in enumerate(data["days"])]
    return patches


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        yield from text_message("Asking the model for trip data (the elements are fixed)…")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        data = yield from ask_until_valid(messages, lambda d: [e.message for e in VALIDATOR.iter_errors(d)], OFFLINE_REPLY)
        patches = to_patches(data)
        result = jr.check("\n".join(json.dumps(p) for p in patches))
        if result["errors"]:
            raise ValueError("; ".join(result["errors"]))
        yield jr.reset()
        for patch in patches:
            yield jr.line(patch)
        yield jr.terminal(result["spec"])
        yield from text_message(f" {len(patches)} JSONL patches: {len(SPEC['elements'])} fixed elements, then the state the model wrote.")

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
