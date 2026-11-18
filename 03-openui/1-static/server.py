"""03 OpenUI · 1 STATIC — a hand-written OpenUI Lang screen; the model only supplies data.

OpenUI Lang is a compact, line-based UI language:   name = Component(arg1, arg2, ...)
A developer can write a screen in it like a template (screen.oui). The model only calls
ONE tool, show_trip(...), with data. The server pours that data into the template and
streams the finished program to the page line by line.

So the model decides WHAT to show; the developer decided HOW it looks.

Run:  python 03-openui/1-static/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

import openui_tools as openui  # noqa: E402
from shared import llm  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message, tool_call  # noqa: E402

TEMPLATE = (HERE / "screen.oui").read_text()  # written by the developer

TRIP_SCHEMA = {
    "type": "object",
    "required": ["title", "days", "budget", "tip"],
    "properties": {
        "title": {"type": "string"},
        "days": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object", "required": ["title", "plan"], "properties": {"title": {"type": "string"}, "plan": {"type": "string"}}},
        },
        "budget": {
            "type": "array",
            "items": {"type": "object", "required": ["category", "amount"], "properties": {"category": {"type": "string"}, "amount": {"type": "number"}}},
        },
        "tip": {"type": "string"},
    },
}
TOOLS = [{"type": "function", "function": {"name": "show_trip", "description": "Show the trip screen with this data.", "parameters": TRIP_SCHEMA}}]

SYSTEM = (
    "You are a trip-planning assistant. Always answer by calling show_trip once with realistic example data. "
    "Each day's plan is 2-4 places joined by ' · '. Budget amounts are rough USD estimates, excluding flights."
)

OFFLINE_REPLY = json.loads((HERE / "offline_reply.json").read_text())

app = create_app(HERE, mounts={"/openui": HERE.parent / "web"})


def fill(template, trip):
    """Pour the tool-call data into the OpenUI Lang template. json.dumps makes valid OpenUI literals."""
    values = {
        "title": trip["title"],
        "n_days": len(trip["days"]),
        "total": f"${sum(b['amount'] for b in trip['budget']):,.0f}",
        "rows": [[str(i + 1), f"{d['title']}: {d['plan']}"] for i, d in enumerate(trip["days"])],
        "labels": [b["category"] for b in trip["budget"]],
        "values": [b["amount"] for b in trip["budget"]],
        "tip": trip["tip"],
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", json.dumps(value, ensure_ascii=False))
    return template


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        reply = llm.chat(messages, tools=TOOLS, fake=OFFLINE_REPLY)
        call = next((c for c in reply["tool_calls"] if c["name"] == "show_trip"), None)
        if call is None:
            yield from text_message(reply["text"] or "The model did not call show_trip.")
            return
        errors = [e.message for e in Draft202012Validator(TRIP_SCHEMA).iter_errors(call["arguments"])]
        if errors:
            raise ValueError("bad show_trip data: " + "; ".join(errors[:3]))

        yield from tool_call("show_trip", call["arguments"], call_id=call["id"])  # visible in the event log
        program = fill(TEMPLATE, call["arguments"])
        problems = openui.check(program)["errors"]
        if problems:  # the template is ours, so this would be a developer bug
            raise ValueError("; ".join(problems))
        yield from openui.stream_lines(program)
        yield from text_message(f"Filled the developer's OpenUI template with the model's data ({len(program.splitlines())} statements).")

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
