"""01 AG-UI · 4 MIXED — catalog components + ONE sandboxed custom region, with actions.

This combines 2-declarative and 3-open-ended:
  * Most of the screen is catalog components (validated, safe, consistent look).
  * At most ONE HtmlFrame holds model-written HTML, for what the catalog cannot express.
  * Clicks close the loop. A Button, or sendAction() inside the HtmlFrame, starts a new
    run with forwardedProps.action. The server checks the action against an ALLOW-LIST
    taken from the spec it sent. A click is a request, not a permission.
  * The first answer is a STATE_SNAPSHOT; updates after a click are STATE_DELTA
    (JSON Patch), so only the changed elements travel.

Run:  python 01-ag-ui/4-mixed/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from ag_ui.core import RunAgentInput  # noqa: E402

from shared import llm  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, state_delta, state_snapshot, stream_run, text_message  # noqa: E402
from shared.catalog import actions_in, catalog_prompt, validate_spec  # noqa: E402
from shared.patch import diff_spec  # noqa: E402

SYSTEM = f"""You design screens for a trip-planning web app.
Reply with ONLY a JSON object (no prose, no code fences):
{{"root": "<id>", "elements": {{"<id>": {{"type": "<Component>", "props": {{...}}, "children": ["<id>", ...]}}}}}}

Allowed components:
{catalog_prompt(allow_html=True)}

Rules:
- The root is a Card. Use catalog components for everything standard.
- Use EXACTLY ONE HtmlFrame, only for an interactive piece the catalog cannot express
  (e.g. a pace slider, a day-by-day timeline, a mini quiz). Inline CSS/JS, no network.
  Inside it, call sendAction('<name>', payload) and list every such name in its "actions".
- Add 1-2 Buttons with short snake_case actions (e.g. "cheaper", "add_day").
- Use realistic example data; budgets are estimates."""

OFFLINE_FIRST = (HERE / "offline_reply.json").read_text()
OFFLINE_AFTER_ACTION = (HERE / "offline_reply_after_action.json").read_text()
MAX_ATTEMPTS = 2

SESSIONS = {}  # thread_id -> {"request": str, "spec": dict}. The server's trusted copy.

app = create_app(HERE)


def check(spec):
    errors = validate_spec(spec, allow_html=True)
    frames = [e for e in spec.get("elements", {}).values() if isinstance(e, dict) and e.get("type") == "HtmlFrame"]
    if len(frames) > 1:
        errors.append("use at most one HtmlFrame")
    return errors


def design_ui(messages, fake):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        reply = llm.chat(messages, json_mode=True, fake=fake)["text"]
        try:
            spec = llm.parse_json(reply)
            errors = check(spec)
        except json.JSONDecodeError as exc:
            errors = [f"not valid JSON: {exc}"]
        yield custom("validation", {"attempt": attempt, "errors": errors})
        if not errors:
            return spec
        messages = messages + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "Rejected:\n- " + "\n- ".join(errors) + "\nReturn the corrected JSON only."},
        ]
    raise ValueError("no valid spec: " + "; ".join(errors))


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action = (run_input.forwarded_props or {}).get("action")
    payload = (run_input.forwarded_props or {}).get("payload")
    session = SESSIONS.get(run_input.thread_id)

    def first_turn():
        request = last_user_text(run_input)
        yield from text_message("Designing: catalog components plus one custom region…")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": request}]
        spec = yield from design_ui(messages, OFFLINE_FIRST)
        SESSIONS[run_input.thread_id] = {"request": request, "spec": spec}
        yield state_snapshot({"ui": spec})
        yield from text_message(f" Done. Actions available: {', '.join(sorted(actions_in(spec)))}.")

    def action_turn():
        allowed = actions_in(session["spec"])
        if action not in allowed:  # the allow-list check
            yield custom("action_blocked", {"action": action, "allowed": sorted(allowed)})
            yield from text_message(f'Blocked: "{action}" is not an action this screen offers.')
            return
        yield from text_message(f'Handling action "{action}"…')
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Original request: {session['request']}\n"
                f"Current screen spec:\n{json.dumps(session['spec'])}\n"
                f'The user triggered action "{action}" with payload {json.dumps(payload)}. '
                "Return the FULL updated spec. Keep unchanged elements identical, with the same ids.",
            },
        ]
        new_spec = yield from design_ui(messages, OFFLINE_AFTER_ACTION)
        ops = diff_spec(session["spec"], new_spec)
        session["spec"] = new_spec
        yield state_delta(ops)
        yield from text_message(f" Updated {len(ops)} element(s) with a STATE_DELTA patch.")

    def expired():
        yield from text_message("That screen came from an earlier server session. Please run your request again.")

    if action:
        return stream_run(run_input, action_turn if session else expired)
    return stream_run(run_input, first_turn)


if __name__ == "__main__":
    serve(app)
