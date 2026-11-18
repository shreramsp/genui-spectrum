"""A minimal MCP Apps HOST: the role Claude Desktop, ChatGPT or Goose play for real.

A host is an MCP CLIENT plus a chat model plus a place to draw views:
  1. connect to the MCP server (trip_server.py over stdio) and list its tools
  2. let the model pick a tool and its arguments                (the host's own model call)
  3. call the tool; read the ui:// resource named in the tool's _meta.ui.resourceUri
  4. hand both to the page, which runs the view in a sandboxed iframe and speaks
     the MCP Apps bridge to it (web/host.js)
  5. when the VIEW calls a tool (tools/call over the bridge), proxy it here, but only
     tools whose _meta.ui.visibility includes "app"

The page and the agent run still talk AG-UI (Parts 01-04), so the same event log shows
the host's work. The MCP connection stays open for the life of the process, like a real host.
"""

import asyncio
import json
import os
import sys
import threading
from pathlib import Path

from ag_ui.core import RunAgentInput
from fastapi import HTTPException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from shared import llm
from shared.agui import create_app, custom, last_user_text, stream_run, text_message, tool_call

HERE = Path(__file__).resolve().parent
SERVER = HERE / "trip_server.py"

MODE_TOOL = {"static": "show_trip_card", "declarative": "design_trip_screen", "open-ended": "build_trip_widget", "mixed": "plan_trip_mixed"}
STATIC_FAKE = json.loads((HERE.parent / "03-openui/1-static/offline_reply.json").read_text())["tool_calls"][0]["arguments"]

SYSTEM = (
    "You are the assistant inside a chat app that can show interactive views from MCP tools. "
    "Answer the user by calling the available tool exactly once. For show_trip_card, invent realistic "
    "trip data (each day's plan is 2-4 places joined by ' · '; budget amounts are rough USD estimates). "
    "For the other tools, pass the user's request as `request`."
)


class McpConnection:
    """One long-lived MCP client session, running on its own event loop thread."""

    def __init__(self, server_path):
        self.server_path = server_path
        self.loop = None
        self.session = None
        self.lock = threading.Lock()

    def _start(self):
        ready = threading.Event()
        self.loop = asyncio.new_event_loop()

        async def main():
            params = StdioServerParameters(command=sys.executable, args=[str(self.server_path)], env=dict(os.environ))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.session = session
                    ready.set()
                    await asyncio.Event().wait()  # keep the connection open until the process exits

        threading.Thread(target=lambda: self.loop.run_until_complete(main()), daemon=True).start()
        if not ready.wait(60):
            raise RuntimeError("the MCP server did not start")

    def run(self, make_coro, timeout=120):
        with self.lock:
            if self.session is None:
                self._start()
        return asyncio.run_coroutine_threadsafe(make_coro(self.session), self.loop).result(timeout)


def dump(model):
    return model.model_dump(by_alias=True, exclude_none=True, mode="json")


def visibility(tool):
    return ((tool.get("_meta") or {}).get("ui") or {}).get("visibility", ["model", "app"])


def create_host(mode, demo_dir):
    """The host app for one mode: the model is offered only that mode's tool."""
    mcp = McpConnection(SERVER)
    app = create_app(demo_dir, mounts={"/host": HERE / "web"})

    def tools():
        return [dump(t) for t in mcp.run(lambda s: s.list_tools()).tools]

    @app.post("/agent")
    def agent(run_input: RunAgentInput):
        def body():
            all_tools = tools()
            offered = [t for t in all_tools if t["name"] == MODE_TOOL[mode] and "model" in visibility(t)]
            schema = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in offered]
            request = last_user_text(run_input)
            fake_args = STATIC_FAKE if mode == "static" else {"request": request}
            fake = {"text": "", "tool_calls": [{"id": "call_1", "name": MODE_TOOL[mode], "arguments": fake_args}]}

            reply = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": request}], tools=schema, fake=fake)
            call = next((c for c in reply["tool_calls"] if c["name"] in {t["name"] for t in offered}), None)
            if call is None:
                yield from text_message(reply["text"] or "The model answered without calling a tool.")
                return
            yield from tool_call(call["name"], call["arguments"], call_id=call["id"])

            tool = next(t for t in all_tools if t["name"] == call["name"])
            result = dump(mcp.run(lambda s: s.call_tool(call["name"], call["arguments"])))
            uri = ((tool.get("_meta") or {}).get("ui") or {}).get("resourceUri")
            resource = None
            if uri:
                content = dump(mcp.run(lambda s: s.read_resource(uri))).get("contents", [{}])[0]
                resource = {"uri": uri, "mimeType": content.get("mimeType"), "html": content.get("text", ""), "meta": content.get("_meta", {})}
            yield custom("mcp_app", {"tool": tool, "arguments": call["arguments"], "result": result, "resource": resource})
            # What a host WITHOUT MCP Apps support would show: the text content.
            text = " ".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
            yield from text_message(f"[{call['name']}] {text}")

        return stream_run(run_input, body)

    @app.post("/tool")
    def view_tool_call(body: dict):
        """tools/call from a VIEW, relayed by the page. Only tools the server marked visible to apps."""
        tool = next((t for t in tools() if t["name"] == body.get("name")), None)
        if tool is None:
            raise HTTPException(403, f"{body.get('name')} is not a tool of this server")
        if "app" not in visibility(tool):
            raise HTTPException(403, f"{tool['name']} is not visible to apps")
        return dump(mcp.run(lambda s: s.call_tool(tool["name"], body.get("arguments") or {})))

    return app
