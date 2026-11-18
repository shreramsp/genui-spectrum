"""The trip MCP server: one tool + one UI view per mode (MCP Apps, SEP-1865).

MCP Apps adds three things to an ordinary MCP server:
  1. a RESOURCE with a ui:// URI and MIME type text/html;profile=mcp-app (the "view")
  2. a TOOL that points at it with _meta.ui.resourceUri
  3. a tool RESULT with `content` (text, for the model) and `structuredContent` (data, for the view)
The HOST reads the view, runs it in a sandboxed iframe and passes it the result over postMessage.
A host that does not know MCP Apps just shows the text. The server needs no web code at all.

    Tool                  View                  Mode         Who decides the UI
    show_trip_card        ui://trip/card.html   static       hand-written view; the HOST's model supplies data as arguments
    design_trip_screen    ui://trip/genui.html  declarative  this server asks Gemini for a catalog spec
    build_trip_widget     ui://trip/genui.html  open-ended   this server asks Gemini for raw HTML (nested sandbox)
    plan_trip_mixed       ui://trip/genui.html  mixed        catalog spec + one HtmlFrame; buttons call update_trip_screen
    update_trip_screen    (app only)            mixed        visibility ["app"]: the view may call it, the model may not

Run it:
    python 05-mcp-apps/trip_server.py          # stdio, for MCP hosts (our web host, Claude Desktop, ...)
"""

import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mcp import types  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from shared import llm  # noqa: E402
from shared.catalog import actions_in, catalog_prompt, validate_spec  # noqa: E402

MIME = "text/html;profile=mcp-app"
CARD_URI = "ui://trip/card.html"
GENUI_URI = "ui://trip/genui.html"
VIEW_META = {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": True}}
ROOT = HERE.parent

# Offline replies (no API key): reuse the saved model answers from Part 01.
OFFLINE_SPEC = (ROOT / "01-ag-ui/2-declarative/offline_reply.json").read_text()
OFFLINE_HTML = (ROOT / "01-ag-ui/3-open-ended/offline_reply.html").read_text()
OFFLINE_MIXED = (ROOT / "01-ag-ui/4-mixed/offline_reply.json").read_text()
OFFLINE_MIXED_AFTER = (ROOT / "01-ag-ui/4-mixed/offline_reply_after_action.json").read_text()

SCREENS = {}  # screen_id -> {"request", "spec"}: the server's own copy, for the action allow-list

server = FastMCP("genui-trip", log_level="WARNING")


# ------------------------------------------------------------ views (resources)


def build_view(template_name):
    """A view must be ONE self-contained HTML document (the host's CSP blocks other files).
    So the view's template gets the shared catalog renderer + sandbox code pasted in."""
    html = (HERE / "views" / template_name).read_text()
    modules = ""
    for path in ["shared/web/sandbox.js", "shared/web/render.js"]:
        code = (ROOT / path).read_text()
        code = "\n".join(line for line in code.splitlines() if not line.startswith("import "))
        modules += code.replace("export function", "function").replace("export const", "const") + "\n"
    html = html.replace("/*SHARED_STYLE*/", (ROOT / "shared/web/style.css").read_text())
    html = html.replace("/*SHARED_RENDERER*/", modules)
    return html.replace("/*VIEW_BRIDGE*/", (HERE / "views" / "view-bridge.js").read_text())


@server.resource(CARD_URI, name="trip_card_view", mime_type=MIME, meta=VIEW_META)
def card_view() -> str:
    """Static mode: a hand-written view. Data arrives later as the tool result."""
    return build_view("card.html")


@server.resource(GENUI_URI, name="trip_genui_view", mime_type=MIME, meta=VIEW_META)
def genui_view() -> str:
    """Generic view: renders a catalog spec, a sandboxed HTML document, or both."""
    return build_view("genui.html")


# ------------------------------------------------------------ helpers


def result(text, data):
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], structuredContent=data)


def ask_for_spec(messages, fake, allow_html):
    """Ask Gemini for a catalog spec; send validation errors back once (correction loop)."""
    errors = []
    for _ in range(2):
        reply = llm.chat(messages, json_mode=True, fake=fake)["text"]
        try:
            spec = llm.parse_json(reply)
            errors = validate_spec(spec, allow_html=allow_html)
            frames = sum(1 for e in spec.get("elements", {}).values() if isinstance(e, dict) and e.get("type") == "HtmlFrame")
            if allow_html and frames != 1:
                errors.append("use exactly one HtmlFrame")
        except (json.JSONDecodeError, AttributeError) as exc:
            errors = [f"not a valid JSON spec: {exc}"]
        if not errors:
            return spec
        messages = messages + [{"role": "assistant", "content": reply}, {"role": "user", "content": "Rejected:\n- " + "\n- ".join(errors) + "\nReturn corrected JSON only."}]
    raise ValueError("model could not produce a valid spec: " + "; ".join(errors))


def spec_prompt(allow_html):
    extra = (
        "\n- Use EXACTLY ONE HtmlFrame for an interactive piece the catalog cannot express; inside it call "
        "sendAction('<name>', payload) and list the names in its \"actions\".\n- Add 1-2 Buttons with snake_case actions."
        if allow_html
        else ""
    )
    return f"""You design screens for a trip-planning app shown inside an MCP host.
Reply with ONLY a JSON object: {{"root": "<id>", "elements": {{"<id>": {{"type": "...", "props": {{...}}, "children": [...]}}}}}}
Allowed components:
{catalog_prompt(allow_html=allow_html)}
Rules: the root is a Card; 5-12 elements; realistic example data; budgets are rough estimates.{extra}"""


HTML_PROMPT = """You build small interactive widgets for a trip-planning app.
Reply with ONLY an HTML fragment (no markdown, no code fences). Inline CSS and JS, no network.
Clean look on a white background, about 650x420 px, with at least one interactive element."""


# ------------------------------------------------------------ tools


@server.tool(meta={"ui": {"resourceUri": CARD_URI}})
def show_trip_card(title: str, days: list[dict], budget: list[dict], tip: str = "") -> types.CallToolResult:
    """STATIC: show a trip card. days = [{"title": str, "plan": str}], budget = [{"category": str, "amount": number}] in USD."""
    total = sum(float(b.get("amount", 0)) for b in budget)
    text = f"{title}: {len(days)} days, about ${total:,.0f}. " + "; ".join(f"Day {i + 1} {d.get('title')}" for i, d in enumerate(days))
    return result(text, {"title": title, "days": days, "budget": budget, "tip": tip, "total": total})


@server.tool(meta={"ui": {"resourceUri": GENUI_URI}})
def design_trip_screen(request: str) -> types.CallToolResult:
    """DECLARATIVE: design a trip screen for the request. The server asks a model for a validated catalog spec."""
    messages = [{"role": "system", "content": spec_prompt(False)}, {"role": "user", "content": request}]
    spec = ask_for_spec(messages, OFFLINE_SPEC, allow_html=False)
    return result(f"Showing a {len(spec['elements'])}-element screen for: {request}", {"mode": "declarative", "spec": spec})


@server.tool(meta={"ui": {"resourceUri": GENUI_URI}})
def build_trip_widget(request: str) -> types.CallToolResult:
    """OPEN-ENDED: build a custom interactive HTML widget for the request."""
    messages = [{"role": "system", "content": HTML_PROMPT}, {"role": "user", "content": request}]
    html = llm.strip_fences(llm.chat(messages, fake=OFFLINE_HTML)["text"])
    return result(f"Showing a custom widget ({len(html):,} characters of HTML) for: {request}", {"mode": "open-ended", "html": html})


@server.tool(meta={"ui": {"resourceUri": GENUI_URI}})
def plan_trip_mixed(request: str) -> types.CallToolResult:
    """MIXED: a catalog screen with one custom HTML region and buttons that update it."""
    messages = [{"role": "system", "content": spec_prompt(True)}, {"role": "user", "content": request}]
    spec = ask_for_spec(messages, OFFLINE_MIXED, allow_html=True)
    screen_id = uuid.uuid4().hex[:12]
    SCREENS[screen_id] = {"request": request, "spec": spec}
    return result(
        f"Showing an interactive trip screen with actions: {', '.join(sorted(actions_in(spec)))}.",
        {"mode": "mixed", "spec": spec, "screenId": screen_id},
    )


@server.tool(meta={"ui": {"resourceUri": GENUI_URI, "visibility": ["app"]}})
def update_trip_screen(screen_id: str, action: str, payload: dict | None = None) -> types.CallToolResult:
    """Called BY THE VIEW when the user clicks something on a plan_trip_mixed screen."""
    screen = SCREENS.get(screen_id)
    if screen is None:
        return types.CallToolResult(content=[types.TextContent(type="text", text="Unknown or expired screen.")], isError=True)
    if action not in actions_in(screen["spec"]):  # a click is a request, not a permission
        return types.CallToolResult(content=[types.TextContent(type="text", text=f'Action "{action}" is not offered by this screen.')], isError=True)
    messages = [
        {"role": "system", "content": spec_prompt(True)},
        {
            "role": "user",
            "content": f"Original request: {screen['request']}\nCurrent spec: {json.dumps(screen['spec'])}\n"
            f'The user triggered "{action}" with payload {json.dumps(payload)}. Return the FULL updated spec, same ids for unchanged elements.',
        },
    ]
    screen["spec"] = ask_for_spec(messages, OFFLINE_MIXED_AFTER, allow_html=True)
    return result(f'Updated the screen after "{action}".', {"mode": "mixed", "spec": screen["spec"], "screenId": screen_id})


if __name__ == "__main__":
    server.run(transport="stdio")
