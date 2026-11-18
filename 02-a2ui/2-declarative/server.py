"""02 A2UI · 2 DECLARATIVE — the model writes the A2UI components AND the data model.

New compared with 1-static:
  * No surface.json. The model designs the structure itself from the Basic Catalog
    (see CATALOG_PROMPT in ../a2ui_messages.py).
  * Every component is validated against the OFFICIAL A2UI v0.9.1 JSON Schema, plus a
    tree check (a "root" exists, every referenced id exists). Errors go back to the model.
  * Two-way binding: inputs (CheckBox, Slider...) write into the page's data model, and a
    Button's action context reads it at click time. Click "Save checklist" to see what the
    page sends back. That action is answered without any model call.

Run:  python 02-a2ui/2-declarative/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import a2ui_messages as a2ui  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message  # noqa: E402
from shared.correct import ask_until_valid  # noqa: E402

SURFACE = "trip"

SYSTEM = f"""You design screens for a trip-planning app using the A2UI protocol.
Reply with ONLY a JSON object: {{"components": [...], "data": {{...}}}}
- "components" is a FLAT list. Exactly one component has "id": "root". Children are referenced by id.
- "data" is the data model. Bind to it with {{"path": "/..."}} instead of repeating values.
- Use a List template for repeated items (e.g. days).
- Use 15-30 components. Include at least one input (CheckBox, Slider, ChoicePicker or TextField)
  and one Button whose action context reads the input's path.

{a2ui.CATALOG_PROMPT}

Use realistic example data; budgets are rough estimates."""

OFFLINE_REPLY = (HERE / "offline_reply.json").read_text()

app = create_app(HERE, mounts={"/a2ui": HERE.parent / "web"})


def check(reply):
    if not isinstance(reply, dict) or not isinstance(reply.get("components"), list):
        return ['reply must be {"components": [...], "data": {...}}']
    if not isinstance(reply.get("data", {}), dict):
        return ['"data" must be an object']
    return a2ui.validate(a2ui.update_components(SURFACE, reply["components"])) + a2ui.tree_errors(reply["components"])


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action = a2ui.action_from(run_input)

    def first_turn():
        yield from text_message("Asking the model to design an A2UI screen…")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        reply = yield from ask_until_valid(messages, check, OFFLINE_REPLY)
        yield from a2ui.as_agui([
            a2ui.create_surface(SURFACE),
            a2ui.update_components(SURFACE, reply["components"]),
            a2ui.update_data_model(SURFACE, reply.get("data", {})),
        ])
        yield from text_message(f" {len(reply['components'])} components, all valid against the official A2UI schema.")

    def action_turn():
        # No model needed: show what the page sent. Context values were read from the data model at click time.
        context = ", ".join(f"{k} = {json.dumps(v)}" for k, v in action.get("context", {}).items()) or "(no context)"
        yield from text_message(
            f'Received A2UI action "{action.get("name")}" from component "{action.get("sourceComponentId")}" with {context}. '
            "(Actions that change the screen are handled in 4-mixed.)"
        )

    return stream_run(run_input, action_turn if action else first_turn)


if __name__ == "__main__":
    serve(app)
