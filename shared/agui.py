"""AG-UI helpers shared by every demo: the "pipe" between agent and page.

An agent run is a stream of typed events sent over Server-Sent Events (SSE):

    RUN_STARTED
      TEXT_MESSAGE_START / TEXT_MESSAGE_CONTENT ... / TEXT_MESSAGE_END    (chat text)
      TOOL_CALL_START / TOOL_CALL_ARGS / TOOL_CALL_END                    (agent calls a tool)
      STATE_SNAPSHOT / STATE_DELTA                                        (shared state)
      CUSTOM                                                              (anything app-specific)
    RUN_FINISHED  (or RUN_ERROR)

We use the official `ag-ui-protocol` package, so the wire format is the real protocol.
"""

import json
import uuid
from pathlib import Path

from ag_ui.core import (
    CustomEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

SHARED_WEB = Path(__file__).resolve().parent / "web"


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------- event builders (each returns a list so callers can `yield from`) ----------


def text_message(text, chunk=40):
    """A whole assistant message, split into CONTENT deltas like a real stream."""
    msg_id = new_id("msg")
    events = [TextMessageStartEvent(message_id=msg_id, role="assistant")]
    for i in range(0, len(text), chunk):
        events.append(TextMessageContentEvent(message_id=msg_id, delta=text[i : i + chunk]))
    events.append(TextMessageEndEvent(message_id=msg_id))
    return events


def tool_call(name, arguments, call_id=None, chunk=80):
    """A tool call whose JSON arguments arrive in ARGS pieces."""
    call_id = call_id or new_id("call")
    args = json.dumps(arguments)
    events = [ToolCallStartEvent(tool_call_id=call_id, tool_call_name=name)]
    for i in range(0, len(args), chunk):
        events.append(ToolCallArgsEvent(tool_call_id=call_id, delta=args[i : i + chunk]))
    events.append(ToolCallEndEvent(tool_call_id=call_id))
    return events


def state_snapshot(state):
    return StateSnapshotEvent(snapshot=state)


def state_delta(patch_ops):
    """RFC 6902 JSON Patch operations, e.g. [{"op": "replace", "path": "/ui/root", "value": "x"}]."""
    return StateDeltaEvent(delta=patch_ops)


def custom(name, value):
    return CustomEvent(name=name, value=value)


# ---------- reading the request ----------


def last_user_text(run_input: RunAgentInput):
    for message in reversed(run_input.messages):
        if message.role == "user":
            return message.content if isinstance(message.content, str) else str(message.content)
    return ""


# ---------- serving ----------


def stream_run(run_input: RunAgentInput, body):
    """Wrap the events from `body()` in RUN_STARTED ... RUN_FINISHED and encode them as SSE."""
    encoder = EventEncoder()

    def events():
        yield encoder.encode(RunStartedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id))
        try:
            for event in body():
                yield encoder.encode(event)
        except Exception as exc:  # the page shows the error instead of hanging
            yield encoder.encode(RunErrorEvent(message=f"{type(exc).__name__}: {exc}"))
            return
        yield encoder.encode(RunFinishedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id))

    return StreamingResponse(events(), media_type=encoder.get_content_type())


def create_app(demo_dir, mounts=None):
    """A FastAPI app: the demo's index.html at /, its app.js at /app.js, shared assets at /shared.

    `mounts` adds more static folders, e.g. {"/part": part_dir / "web"} for code shared by one part.
    """
    demo_dir = Path(demo_dir)
    app = FastAPI()
    app.mount("/shared", StaticFiles(directory=SHARED_WEB), name="shared")
    for url, folder in (mounts or {}).items():
        app.mount(url, StaticFiles(directory=folder), name=url.strip("/"))

    @app.get("/")
    def index():
        return FileResponse(demo_dir / "index.html")

    @app.get("/app.js")
    def app_js():
        return FileResponse(demo_dir / "app.js", media_type="text/javascript")

    return app


def serve(app, default_port=8000):
    import os

    import uvicorn

    port = int(os.environ.get("PORT", default_port))
    print(f"\n  Open http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
