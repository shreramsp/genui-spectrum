"""01 AG-UI · 1 STATIC — the agent picks a ready-made component and fills in its data.

The developer wrote three components in advance (see app.js). To the model they are
just three TOOLS. When the model "calls" show_itinerary(...), we forward that call to
the page as AG-UI TOOL_CALL events, and the page draws its pre-built itinerary card.

The model decides WHICH component and WHAT data. It never decides the layout.

Run:  python 01-ag-ui/1-static/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # repo root, so `import shared` works

from ag_ui.core import RunAgentInput  # noqa: E402

from shared import llm  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message, tool_call  # noqa: E402

# Each tool = one pre-built component on the page. The JSON Schema is the component's props.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "show_itinerary",
            "description": "Show a day-by-day itinerary card.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "days": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "integer"},
                                "title": {"type": "string"},
                                "activities": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["day", "title", "activities"],
                        },
                    },
                },
                "required": ["city", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_budget",
            "description": "Show an estimated budget card with a bar per category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "currency": {"type": "string", "description": "e.g. USD"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"category": {"type": "string"}, "amount": {"type": "number"}},
                            "required": ["category", "amount"],
                        },
                    },
                },
                "required": ["city", "currency", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_packing_list",
            "description": "Show a packing checklist card.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}}},
                "required": ["city", "items"],
            },
        },
    },
]
TOOL_NAMES = {t["function"]["name"] for t in TOOLS}

SYSTEM = (
    "You are a trip-planning assistant inside a web app. The app can only display information "
    "through its tools: show_itinerary, show_budget and show_packing_list. Call the one or more "
    "tools that best answer the user, with realistic example data. Also write ONE short sentence "
    "of plain text for the user. Budgets are rough estimates."
)

OFFLINE_REPLY = json.loads((HERE / "offline_reply.json").read_text())

app = create_app(HERE)


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        reply = llm.chat(messages, tools=TOOLS, fake=OFFLINE_REPLY)

        yield from text_message(reply["text"] or "Here is what I found.")
        for call in reply["tool_calls"]:
            if call["name"] not in TOOL_NAMES:  # never forward a tool the page does not have
                yield from text_message(f"(ignored unknown tool {call['name']})")
                continue
            yield from tool_call(call["name"], call["arguments"], call_id=call["id"])

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
