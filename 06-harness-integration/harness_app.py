"""The harness's WEB surface: the same agent loop (harness.py), streamed to the page as AG-UI.

The page sees the whole loop in its event log:
    STEP_STARTED -> TOOL_CALL_* list_files -> TOOL_CALL_RESULT -> STEP_FINISHED -> ...
    ... -> TOOL_CALL_* render_ui -> CUSTOM render {kind, ...} -> STEP_FINISHED

Mixed mode keeps the conversation per thread. A click on the generated UI is checked against
the actions that UI offered, then added to the SAME conversation as a user message, so the
agent can read more files before it re-renders.
"""

import json
from pathlib import Path

from ag_ui.core import RunAgentInput

import harness
from shared.agui import create_app, custom, last_user_text, stream_run, text_message

HERE = Path(__file__).resolve().parent
SESSIONS = {}  # thread_id -> {"messages": [...], "ui": last rendered UI}


def create_harness_app(mode, demo_dir):
    demo_dir = Path(demo_dir)
    script = json.loads((demo_dir / "offline_script.json").read_text())
    action_file = demo_dir / "offline_script_action.json"
    action_script = json.loads(action_file.read_text()) if action_file.exists() else []
    app = create_app(demo_dir, mounts={"/harness": HERE / "web"})

    @app.post("/agent")
    def agent(run_input: RunAgentInput):
        props = run_input.forwarded_props or {}
        action, payload = props.get("action"), props.get("payload")
        session = SESSIONS.get(run_input.thread_id)

        def first_turn():
            messages = [{"role": "system", "content": harness.system_prompt(mode)}, {"role": "user", "content": last_user_text(run_input)}]
            ui = yield from harness.agent_turn(mode, messages, script)
            SESSIONS[run_input.thread_id] = {"messages": harness.trim(messages), "ui": ui}

        def action_turn():
            allowed = harness.ui_actions(session["ui"])
            if action not in allowed:  # a click is a request, not a permission
                yield custom("action_blocked", {"action": action, "allowed": sorted(allowed)})
                yield from text_message(f'Blocked: "{action}" is not an action the current UI offers.')
                return
            session["messages"].append({"role": "user", "content": f'[UI action] The user clicked "{action}" with payload {json.dumps(payload)}. Update the UI.'})
            ui = yield from harness.agent_turn(mode, session["messages"], action_script)
            session["messages"] = harness.trim(session["messages"])
            session["ui"] = ui or session["ui"]

        def expired():
            yield from text_message("That UI came from an earlier server session. Please run your request again.")

        if action:
            return stream_run(run_input, action_turn if session else expired)
        return stream_run(run_input, first_turn)

    return app
