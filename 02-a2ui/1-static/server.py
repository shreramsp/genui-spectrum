"""02 A2UI · 1 STATIC — a fixed A2UI screen; the model only fills in the DATA MODEL.

A2UI splits a UI into STRUCTURE (updateComponents) and DATA (updateDataModel).
In static mode the developer owns the structure completely: surface.json is written
by hand and never changes. The model only writes data in a fixed shape, which the
components display through bindings such as {"path": "/trip/title"}.

Watch the event log:
  1. createSurface + updateComponents arrive at once (before the model even answers),
     so the empty skeleton appears instantly.
  2. updateDataModel /trip arrives when the model is done, and fills it in.
  3. Move the slider / pick a style, click "Re-plan": an A2UI action goes back, and the
     answer is ONLY a new updateDataModel. The structure is never resent.

Run:  python 02-a2ui/1-static/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]  # repo root (shared) + this part (a2ui_messages)

from ag_ui.core import RunAgentInput  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

import a2ui_messages as a2ui  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402
from shared.correct import ask_until_valid  # noqa: E402

SURFACE = "trip"
COMPONENTS = json.loads((HERE / "surface.json").read_text())  # written by the developer

# The ONLY thing the model may produce: data in this exact shape.
DATA_SCHEMA = {
    "type": "object",
    "required": ["title", "summary", "days", "budget", "total"],
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "days": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "activities"],
                "additionalProperties": False,
                "properties": {"title": {"type": "string"}, "activities": {"type": "string"}},
            },
        },
        "budget": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["category", "amount"],
                "additionalProperties": False,
                "properties": {"category": {"type": "string"}, "amount": {"type": "string"}},
            },
        },
        "total": {"type": "string"},
    },
}
DATA_VALIDATOR = Draft202012Validator(DATA_SCHEMA)

SYSTEM = """You fill in the DATA for a fixed trip-planner screen. Reply with ONLY a JSON object:
{"title": str, "summary": str (one sentence),
 "days": [{"title": "Day 1 · <theme>", "activities": "<a> · <b> · <c>"}],
 "budget": [{"category": str, "amount": "$<number>"}],
 "total": "Total ≈ $<number>"}
Use realistic example data. Budgets are rough estimates in USD, excluding flights."""

OFFLINE_FIRST = (HERE / "offline_reply.json").read_text()
OFFLINE_REPLAN = (HERE / "offline_reply_replan.json").read_text()

SESSIONS = {}  # thread_id -> the original request

app = create_app(HERE, mounts={"/a2ui": HERE.parent / "web"})


def check_data(days_wanted):
    def check(data):
        errors = [f'{"/".join(map(str, e.absolute_path)) or "(root)"}: {e.message}' for e in DATA_VALIDATOR.iter_errors(data)]
        if not errors and days_wanted and len(data["days"]) != days_wanted:
            errors.append(f"days must have exactly {days_wanted} entries")
        return errors

    return check


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action = a2ui.action_from(run_input)

    def first_turn():
        request = last_user_text(run_input)
        SESSIONS[run_input.thread_id] = request
        # Structure first: it does not depend on the model at all.
        yield from a2ui.as_agui([a2ui.create_surface(SURFACE), a2ui.update_components(SURFACE, COMPONENTS)])
        yield from text_message("Screen structure sent. Asking the model for the data…")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": request}]
        data = yield from ask_until_valid(messages, check_data(None), OFFLINE_FIRST)
        yield from a2ui.as_agui([
            a2ui.update_data_model(SURFACE, {"days": len(data["days"]), "style": ["comfort"]}, path="/form"),
            a2ui.update_data_model(SURFACE, data, path="/trip"),
        ])
        yield from text_message(" Data model filled in.")

    def action_turn():
        if action.get("name") not in a2ui.actions_in(COMPONENTS):
            yield custom("action_blocked", {"action": action.get("name")})
            yield from text_message(f'Blocked: "{action.get("name")}" is not an action on this screen.')
            return
        days = int(action["context"].get("days") or 3)
        style = (action["context"].get("style") or ["comfort"])[0]
        yield from text_message(f"Re-planning: {days} days, {style} style. Only the data changes…")
        request = SESSIONS.get(run_input.thread_id, "a trip")
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{request}\nMake it exactly {days} days, {style} travel style."},
        ]
        data = yield from ask_until_valid(messages, check_data(days), OFFLINE_REPLAN if days == 5 else OFFLINE_FIRST)
        yield from a2ui.as_agui([a2ui.update_data_model(SURFACE, data, path="/trip")])
        yield from text_message(" Done: one updateDataModel, zero component changes.")

    return stream_run(run_input, action_turn if action else first_turn)


if __name__ == "__main__":
    serve(app)
