"""03 OpenUI · 3 OPEN-ENDED — the model writes raw HTML; OpenUI carries it in an HtmlArtifact.

OpenUI's own answer to open-ended UI is a component that holds a whole HTML document as a
string argument (OpenUI's examples call it HtmlArtifact). Here:

  1. The server opens the program:   root = Stack([intro, widget])
                                     widget = HtmlArtifact("Trip widget", "
  2. The model's HTML streams INSIDE that string literal (each piece JSON-escaped), so the
     page shows the raw source growing while useIsStreaming() is true...
  3. ...then the server closes the string:  ")  and the finished document runs in the sandbox.

Run:  python 03-openui/3-open-ended/server.py   then open http://localhost:8000
"""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import openui_tools as openui  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message  # noqa: E402

SYSTEM = """You build small interactive widgets for a trip-planning web app.
Reply with ONLY an HTML fragment (no markdown, no code fences, no <html> or <head>).
Inline all CSS in one <style> tag and all JavaScript in one <script> tag.
It runs in a sandbox with NO network: no external scripts, fonts, images or fetch().
Use a clean, modern look on a white background, fit in about 700x450 pixels, and make
at least one thing interactive (tabs, a checklist, a slider, a toggle...).
Use realistic example data; budgets are estimates."""

OPEN = 'root = Stack([intro, widget])\nintro = Text("Everything below was written as raw HTML by the model.", "small")\nwidget = HtmlArtifact("Trip widget", "'
CLOSE = '")\n'

OFFLINE_REPLY = (HERE / "offline_reply.html").read_text()

app = create_app(HERE, mounts={"/openui": HERE.parent / "web"})


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        started = time.perf_counter()
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        yield openui.delta(OPEN)
        html = yield from openui.stream_program(messages, OFFLINE_REPLY, escape=True)
        yield openui.delta(CLOSE)
        program = OPEN + json.dumps(html, ensure_ascii=False)[1:-1] + CLOSE
        errors = openui.check(program, allow_html=True)["errors"]
        if errors:
            raise ValueError("; ".join(errors))
        yield from text_message(
            f"{len(html):,} characters of HTML in {time.perf_counter() - started:.1f}s, streamed inside one OpenUI HtmlArtifact "
            "statement, then run in a sandboxed iframe."
        )

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
