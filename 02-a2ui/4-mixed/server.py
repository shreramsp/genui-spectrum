"""02 A2UI · 4 MIXED — Basic Catalog components + ONE HtmlFrame, with A2UI actions.

Combines 2-declarative (validated catalog components, data binding) and 3-open-ended
(one model-written HtmlFrame in a sandbox). Then it closes the loop:

  click a Button, or call sendAction() inside the HtmlFrame
    -> the page sends an A2UI action message {name, surfaceId, sourceComponentId, context}
    -> the server checks the name against ITS OWN copy of the screen (allow-list)
    -> the model answers with ONLY the changed components and/or the new data
    -> the server sends updateComponents (upsert by id) and/or updateDataModel

That is A2UI's built-in incremental update: components are replaced by id, so there is
no need for a separate patch format like AG-UI's STATE_DELTA.

Run:  python 02-a2ui/4-mixed/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import a2ui_messages as a2ui  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402
from shared.correct import ask_until_valid  # noqa: E402

SURFACE = "trip"

HTMLFRAME_DOC = """- HtmlFrame (custom): html (an HTML fragment with inline <style>/<script>, NO network), height? (px),
  actions (list of names). Inside the HTML, call sendAction('<name>', {...}) for each name in actions."""

SYSTEM = f"""You design screens for a trip-planning app using the A2UI protocol with a custom catalog.
Reply with ONLY a JSON object: {{"components": [...], "data": {{...}}}}
- "components" is a FLAT list; exactly one has "id": "root"; children are referenced by id.
- "data" is the data model; bind with {{"path": "/..."}}. Use a List template for repeated items.
- Use EXACTLY ONE HtmlFrame, only for an interactive piece the catalog cannot express
  (e.g. a pace slider with a live preview, a mini map grid, a quiz).
- Add one Button with a snake_case action (e.g. "cheaper").

{a2ui.CATALOG_PROMPT}
{HTMLFRAME_DOC}

Use realistic example data; budgets are rough estimates."""

UPDATE_RULES = """Reply with ONLY {"components": [ONLY new or changed components, full objects, same ids], "data": <the FULL new data model, or omit if unchanged>}.
Do not resend unchanged components."""

OFFLINE_FIRST = (HERE / "offline_reply.json").read_text()
OFFLINE_AFTER_ACTION = (HERE / "offline_reply_after_action.json").read_text()

SESSIONS = {}  # thread_id -> {"request", "components": {id: component}, "data"}. The server's trusted copy.

app = create_app(HERE, mounts={"/a2ui": HERE.parent / "web"})


def screen_errors(components, data):
    errors = a2ui.validate(a2ui.update_components(SURFACE, components), allow_html=True) + a2ui.tree_errors(components)
    frames = sum(1 for c in components if isinstance(c, dict) and c.get("component") == "HtmlFrame")
    if frames != 1:
        errors.append(f"use exactly one HtmlFrame (found {frames})")
    if not isinstance(data, dict):
        errors.append('"data" must be an object')
    return errors


def first_check(reply):
    if not isinstance(reply, dict) or not isinstance(reply.get("components"), list):
        return ['reply must be {"components": [...], "data": {...}}']
    return screen_errors(reply["components"], reply.get("data", {}))


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action = a2ui.action_from(run_input)
    session = SESSIONS.get(run_input.thread_id)

    def first_turn():
        request = last_user_text(run_input)
        yield from text_message("Designing: Basic Catalog components plus one HtmlFrame…")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": request}]
        reply = yield from ask_until_valid(messages, first_check, OFFLINE_FIRST)
        components, data = reply["components"], reply.get("data", {})
        SESSIONS[run_input.thread_id] = {"request": request, "components": {c["id"]: c for c in components}, "data": data}
        yield from a2ui.as_agui([
            a2ui.create_surface(SURFACE, a2ui.TRIP_CATALOG_ID),
            a2ui.update_components(SURFACE, components),
            a2ui.update_data_model(SURFACE, data),
        ])
        yield from text_message(f" Done. Actions on this screen: {', '.join(sorted(a2ui.actions_in(components)))}.")

    def action_turn():
        name = action.get("name")
        allowed = a2ui.actions_in(session["components"].values())
        if name not in allowed:  # a click is a request, not a permission
            yield custom("action_blocked", {"action": name, "allowed": sorted(allowed)})
            yield from text_message(f'Blocked: "{name}" is not an action this screen offers.')
            return
        yield from text_message(f'Handling A2UI action "{name}"…')

        def update_check(reply):
            if not isinstance(reply, dict) or not isinstance(reply.get("components", []), list):
                return ['reply must be {"components": [...], "data": {...}}']
            merged = {**session["components"], **{c.get("id"): c for c in reply.get("components", []) if isinstance(c, dict)}}
            return screen_errors(list(merged.values()), reply.get("data", session["data"]))

        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Original request: {session['request']}\n"
                f"Current components: {json.dumps(list(session['components'].values()))}\n"
                f"Current data: {json.dumps(session['data'])}\n"
                f"The user triggered this A2UI action: {json.dumps(action)}\n{UPDATE_RULES}",
            },
        ]
        reply = yield from ask_until_valid(messages, update_check, OFFLINE_AFTER_ACTION)
        changed = reply.get("components", [])
        session["components"].update({c["id"]: c for c in changed})
        out = [a2ui.update_components(SURFACE, changed)] if changed else []
        if "data" in reply:
            session["data"] = reply["data"]
            out.append(a2ui.update_data_model(SURFACE, reply["data"]))
        yield from a2ui.as_agui(out)
        yield from text_message(
            f" Sent {len(changed)} changed component(s) of {len(session['components'])}"
            + (" and a new data model." if "data" in reply else ".")
        )

    def expired():
        yield from text_message("That screen came from an earlier server session. Please run your request again.")

    if action:
        return stream_run(run_input, action_turn if session else expired)
    return stream_run(run_input, first_turn)


if __name__ == "__main__":
    serve(app)
