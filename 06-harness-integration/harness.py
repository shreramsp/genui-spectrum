"""A small, BOUNDED agent harness with generative UI as a tool.

A coding-agent harness is a loop:   model -> tool calls -> tool results -> model -> ... -> answer.
Here the agent works on a small project folder (sample_trip/) with two file tools, and
answers by calling a RENDER tool. The render tool is where generative UI joins the loop:

    mode         render tool                                  what the agent decides
    static       show_budget(...) / show_bookings(...)        which pre-built view + its data
    declarative  render_ui(spec_json)                         the layout, from the shared catalog
    open-ended   render_html(html)                            everything (raw HTML, sandboxed)
    mixed        render_ui(spec_json) incl. one HtmlFrame     layout + one custom region; clicks come
                                                              back into the SAME conversation

Invalid UI is not an exception: the validator's errors become the tool RESULT, and the agent
fixes its own spec on the next step. That is the harness's built-in correction loop.

Safety limits (so it cannot wander off or run up a bill):
  * file tools only see sample_trip/ (no "..", no absolute paths), reads capped at 4 KB
  * at most MAX_STEPS model calls per turn; every call goes through the $ cap in shared/llm.py

Two surfaces, one agent:
  * web:       each mode folder's server.py streams the run as AG-UI events (steps, tool calls, UI)
  * terminal:  python 06-harness-integration/harness.py --mode declarative "Summarize my spending"
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ag_ui.core import StepFinishedEvent, StepStartedEvent, ToolCallResultEvent  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from shared import llm  # noqa: E402
from shared.agui import custom, new_id, text_message, tool_call  # noqa: E402
from shared.catalog import actions_in, catalog_prompt, validate_spec  # noqa: E402
from shared.terminal import render_terminal  # noqa: E402

WORKSPACE = HERE / "sample_trip"
MAX_STEPS = 6
MAX_READ = 4000
MAX_HISTORY = 24  # messages kept per conversation (mixed mode)

# ------------------------------------------------------------ tools


def fn(name, description, properties, required=()):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": list(required)}}}


FILE_TOOLS = [
    fn("list_files", "List the files in the trip project folder.", {}),
    fn("read_file", "Read one file from the trip project folder (max 4 KB).", {"path": {"type": "string", "description": "file name, e.g. expenses.csv"}}, ["path"]),
]

BUDGET_SCHEMA = {
    "title": {"type": "string"},
    "items": {"type": "array", "items": {"type": "object", "properties": {"category": {"type": "string"}, "amount": {"type": "number"}}, "required": ["category", "amount"]}},
}
BOOKINGS_SCHEMA = {
    "rows": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"type": {"type": "string"}, "name": {"type": "string"}, "date": {"type": "string"}, "price": {"type": "number"}, "status": {"type": "string"}},
            "required": ["type", "name", "date", "price", "status"],
        },
    }
}

RENDER_TOOLS = {
    "static": [
        fn("show_budget", "Show the pre-built budget view: total + one bar per category (USD).", BUDGET_SCHEMA, ["title", "items"]),
        fn("show_bookings", "Show the pre-built bookings table.", BOOKINGS_SCHEMA, ["rows"]),
    ],
    "declarative": [fn("render_ui", "Show a UI built from the catalog. Pass the spec as a JSON string.", {"spec_json": {"type": "string"}}, ["spec_json"])],
    "open-ended": [fn("render_html", "Show a custom HTML widget (inline CSS/JS, no network) in a sandbox.", {"html": {"type": "string"}}, ["html"])],
    "mixed": [fn("render_ui", "Show a UI built from the catalog incl. at most one HtmlFrame. Pass the spec as a JSON string.", {"spec_json": {"type": "string"}}, ["spec_json"])],
}


def system_prompt(mode):
    base = (
        "You are a trip assistant working on the user's trip project folder. Use list_files and read_file "
        "to look at the real data first, then answer by calling the render tool ONCE with the result. "
        "Use only numbers from the files. Be efficient: read only the files you need."
    )
    if mode in ("declarative", "mixed"):
        spec = '{"root": "<id>", "elements": {"<id>": {"type": "...", "props": {...}, "children": [...]}}}'
        extra = ""
        if mode == "mixed":
            extra = (
                "\nInclude ONE HtmlFrame for an interactive piece (e.g. a what-if budget slider); inside it call "
                "sendAction('<name>', payload) and list the names in its \"actions\". Add one Button with a snake_case action."
            )
        return f"{base}\n\nrender_ui takes spec_json = a JSON string of {spec}\nThe root is a Card. Allowed components:\n{catalog_prompt(allow_html=mode == 'mixed')}{extra}"
    if mode == "open-ended":
        return f"{base}\n\nrender_html takes an HTML fragment with inline <style>/<script>, no network, about 700x450 px, interactive."
    return base


def safe_path(name):
    path = (WORKSPACE / str(name)).resolve()
    if path.parent != WORKSPACE.resolve() or not path.is_file():
        raise ValueError(f"{name!r} is not a file in the project folder")
    return path


def run_tool(mode, name, args):
    """Execute one tool. Returns (text result for the model, UI to render or None)."""
    if name == "list_files":
        return "\n".join(f"{p.name} ({p.stat().st_size} bytes)" for p in sorted(WORKSPACE.iterdir()) if p.is_file()), None
    if name == "read_file":
        return safe_path(args.get("path")).read_text()[:MAX_READ], None
    if name in ("show_budget", "show_bookings"):
        schema = {"type": "object", "properties": BUDGET_SCHEMA if name == "show_budget" else BOOKINGS_SCHEMA, "required": ["items"] if name == "show_budget" else ["rows"]}
        errors = [e.message for e in Draft202012Validator(schema).iter_errors(args)]
        if errors:
            return "REJECTED: " + "; ".join(errors[:5]), None
        return f"Shown: {name}.", {"kind": "component", "name": name, "props": args}
    if name == "render_ui":
        try:
            spec = llm.parse_json(args.get("spec_json", ""))
        except json.JSONDecodeError as exc:
            return f"REJECTED: spec_json is not valid JSON ({exc}). Call render_ui again.", None
        errors = validate_spec(spec, allow_html=mode == "mixed")
        frames = sum(1 for e in spec.get("elements", {}).values() if isinstance(e, dict) and e.get("type") == "HtmlFrame")
        if frames > 1:
            errors.append("use at most one HtmlFrame")
        if errors:
            return "REJECTED, fix these and call render_ui again:\n- " + "\n- ".join(errors[:10]), None
        return f"Shown: {len(spec['elements'])} components.", {"kind": "spec", "spec": spec}
    if name == "render_html":
        html = llm.strip_fences(args.get("html", ""))
        return f"Shown: {len(html):,} characters of HTML in a sandbox.", {"kind": "html", "html": html}
    return f"REJECTED: unknown tool {name}", None


# ------------------------------------------------------------ the loop


def agent_turn(mode, messages, script):
    """Generator: run the loop until a UI is rendered, the model answers in text, or MAX_STEPS.

    Yields AG-UI events. `messages` is updated in place. `script` = offline replies, one per step.
    Returns the last rendered UI (or None).
    """
    tools = FILE_TOOLS + RENDER_TOOLS[mode]
    for step in range(MAX_STEPS):
        yield StepStartedEvent(step_name=f"step {step + 1}")
        fake = script[step] if step < len(script) else {"text": "(offline script finished)", "tool_calls": []}
        reply = llm.chat(messages, tools=tools, fake=fake)
        if reply["text"]:
            yield from text_message(reply["text"])
        if not reply["tool_calls"]:
            messages.append({"role": "assistant", "content": reply["text"]})
            yield StepFinishedEvent(step_name=f"step {step + 1}")
            return None
        messages.append(reply.get("assistant_message") or {  # live: the model's raw message (keeps Gemini's thought signatures)
            "role": "assistant",
            "content": reply["text"] or None,
            "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in reply["tool_calls"]],
        })
        rendered = None
        for call in reply["tool_calls"]:
            yield from tool_call(call["name"], call["arguments"], call_id=call["id"])
            try:
                output, ui = run_tool(mode, call["name"], call["arguments"])
            except ValueError as exc:
                output, ui = f"ERROR: {exc}", None
            yield ToolCallResultEvent(message_id=new_id("msg"), tool_call_id=call["id"], content=output[:400], role="tool")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
            if ui:
                rendered = ui
                yield custom("render", ui)
        yield StepFinishedEvent(step_name=f"step {step + 1}")
        if rendered:  # a successful render ends the turn: no extra model call needed
            return rendered
    yield from text_message(f"Stopped after {MAX_STEPS} steps (the harness limit).")
    return None


def trim(messages):
    """Keep the system prompt + the most recent messages, never starting on a tool result."""
    if len(messages) <= MAX_HISTORY:
        return messages
    rest = messages[-(MAX_HISTORY - 1):]
    while rest and rest[0]["role"] == "tool":
        rest = rest[1:]
    return [messages[0]] + rest


def ui_actions(ui):
    return actions_in(ui["spec"]) if ui and ui.get("kind") == "spec" else set()


# ------------------------------------------------------------ terminal surface


def draw_in_terminal(ui):
    if ui["kind"] == "spec":
        return render_terminal(ui["spec"])
    if ui["kind"] == "html":
        return f"[ {len(ui['html']):,} characters of HTML: open the web page to run it ]"
    props = ui["props"]
    if ui["name"] == "show_budget":
        top = max([i["amount"] for i in props["items"]] or [1])
        lines = [f"┌─ {props['title']}  (total ${sum(i['amount'] for i in props['items']):,.0f})"]
        lines += [f"│ {i['category']:<12} {'█' * max(1, round(24 * i['amount'] / top))} {i['amount']:,.0f}" for i in props["items"]]
        return "\n".join(lines + ["└" + "─" * 20])
    return "\n".join(["┌─ Bookings"] + [f"│ {r['date']}  {r['type']:<9} {r['name']:<32} ${r['price']:>6,.0f}  {r['status']}" for r in props["rows"]] + ["└" + "─" * 20])


def main():
    parser = argparse.ArgumentParser(description="Run the harness in the terminal.")
    parser.add_argument("request")
    parser.add_argument("--mode", choices=list(RENDER_TOOLS), default="declarative")
    cli = parser.parse_args()
    script = json.loads((HERE / {"static": "1-static", "declarative": "2-declarative", "open-ended": "3-open-ended", "mixed": "4-mixed"}[cli.mode] / "offline_script.json").read_text())
    messages = [{"role": "system", "content": system_prompt(cli.mode)}, {"role": "user", "content": cli.request}]
    print(f"model={llm.MODEL} offline={llm.OFFLINE} mode={cli.mode}\n")
    run = agent_turn(cli.mode, messages, script)
    ui = None
    try:
        while True:
            event = next(run)
            kind = event.type.value if hasattr(event.type, "value") else str(event.type)
            if kind == "STEP_STARTED":
                print(f"── {event.step_name}")
            elif kind == "TOOL_CALL_START":
                print(f"   tool: {event.tool_call_name}")
            elif kind == "TOOL_CALL_RESULT":
                print("   → " + event.content.splitlines()[0][:90])
    except StopIteration as done:
        ui = done.value
    print()
    print(draw_in_terminal(ui) if ui else "(no UI rendered)")
    if not llm.OFFLINE:
        print(f"\nGemini spend so far: ${llm.spent():.4f} of ${llm.SPEND_LIMIT_USD:.2f}")


if __name__ == "__main__":
    main()
