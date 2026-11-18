"""01 AG-UI · 2 DECLARATIVE — the agent designs the layout from a catalog of allowed parts.

New compared with 1-static:
  * The model no longer picks one finished component. It writes a JSON "spec" that
    arranges catalog components (Card, Row, Metric, Table, BarChart, ...).
  * The server VALIDATES the spec against the catalog. If it is wrong, the errors go
    back to the model for one more try (a correction loop).
  * The finished spec is sent as AG-UI SHARED STATE (STATE_SNAPSHOT). The page just
    renders whatever is in state.ui.

Run:  python 01-ag-ui/2-declarative/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from ag_ui.core import RunAgentInput  # noqa: E402

from shared import llm  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, state_snapshot, stream_run, text_message  # noqa: E402
from shared.catalog import catalog_prompt, validate_spec  # noqa: E402

SYSTEM = f"""You design screens for a trip-planning web app.
Reply with ONLY a JSON object of this shape (no prose, no code fences):
{{"root": "<id>", "elements": {{"<id>": {{"type": "<Component>", "props": {{...}}, "children": ["<id>", ...]}}}}}}

Allowed components (use nothing else, use exact prop names):
{catalog_prompt(allow_html=False)}

Rules: the root is a Card. Use 5-12 elements. Use realistic example data; budgets are estimates.
Every id in "children" must exist in "elements"."""

MAX_ATTEMPTS = 2
OFFLINE_REPLY = (HERE / "offline_reply.json").read_text()

app = create_app(HERE)


def design_ui(user_text):
    """Ask the model for a spec, validate it, and give it one chance to fix mistakes.

    Yields AG-UI events along the way and finally returns the valid spec.
    """
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        reply = llm.chat(messages, json_mode=True, fake=OFFLINE_REPLY)["text"]
        try:
            spec = llm.parse_json(reply)
            errors = validate_spec(spec)
        except json.JSONDecodeError as exc:
            spec, errors = None, [f"not valid JSON: {exc}"]

        yield custom("validation", {"attempt": attempt, "errors": errors})
        if not errors:
            return spec
        # Errors are just another message: the model reads them and tries again.
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "Your spec was rejected:\n- " + "\n- ".join(errors) + "\nReturn the corrected JSON only."},
        ]
    raise ValueError("model could not produce a valid spec: " + "; ".join(errors))


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        yield from text_message("Designing a layout from the catalog…")
        spec = yield from design_ui(last_user_text(run_input))
        yield state_snapshot({"ui": spec})
        yield from text_message(f" Done: {len(spec['elements'])} components, all validated against the catalog.")

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
