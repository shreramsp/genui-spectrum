"""04 json-render · 3 OPEN-ENDED — the model writes raw HTML; it travels as one HtmlFrame element.

json-render only draws components that are in the catalog. To allow open-ended UI we add an
HtmlFrame component to the catalog (web/catalog.mjs, allowHtml) and give it a renderer that
runs the HTML in the shared sandbox. The model writes HTML; the server sends two patches:
    {"op":"add","path":"/root","value":"frame-1"}
    {"op":"add","path":"/elements/frame-1","value":{"type":"HtmlFrame","props":{"html":"..."}, ...}}

Run:  python 04-json-render/3-open-ended/server.py   then open http://localhost:8000
"""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import jr_tools as jr  # noqa: E402
from shared import llm  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message  # noqa: E402

SYSTEM = """You build small interactive widgets for a trip-planning web app.
Reply with ONLY an HTML fragment (no markdown, no code fences, no <html> or <head>).
Inline all CSS in one <style> tag and all JavaScript in one <script> tag.
It runs in a sandbox with NO network: no external scripts, fonts, images or fetch().
Use a clean, modern look on a white background, fit in about 700x450 pixels, and make
at least one thing interactive (tabs, a checklist, a slider, a toggle...).
Use realistic example data; budgets are estimates."""

OFFLINE_REPLY = (HERE / "offline_reply.html").read_text()

app = create_app(HERE, mounts={"/jr": HERE.parent / "web"})


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        yield from text_message("The model is writing raw HTML…")
        started = time.perf_counter()
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        html = llm.strip_fences("".join(llm.stream(messages, fake=OFFLINE_REPLY)))
        frame = {"type": "HtmlFrame", "props": {"html": html, "height": 480, "actions": None}, "children": []}
        patches = [{"op": "add", "path": "/root", "value": "frame-1"}, {"op": "add", "path": "/elements/frame-1", "value": frame}]
        result = jr.check("\n".join(map(json.dumps, patches)), allow_html=True)
        if result["errors"]:
            raise ValueError("; ".join(result["errors"]))
        yield jr.reset()
        for patch in patches:
            yield jr.line(patch)
        yield jr.terminal(result["spec"])
        yield from text_message(
            f" {len(html):,} characters of HTML in {time.perf_counter() - started:.1f}s, carried by one HtmlFrame element. "
            "The terminal renderer cannot run HTML: open-ended UI only works on targets with a browser."
        )

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
