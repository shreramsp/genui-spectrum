"""02 A2UI · 3 OPEN-ENDED — A2UI has no "raw HTML" component, so we ADD one to the catalog.

A2UI is deliberately declarative: the Basic Catalog has no way to run model-written code.
The protocol's answer is CUSTOM CATALOGS: createSurface names a catalogId, and the client
must support every component in that catalog. Our catalog TRIP_CATALOG_ID is the Basic
Catalog plus one component:

    {"id": "root", "component": "HtmlFrame", "html": "<model-written HTML>", "height": 480}

The model writes the HTML; the server wraps it in ordinary A2UI messages; the page's A2UI
client draws HtmlFrame inside the same sandbox as 01-ag-ui/3-open-ended.

Run:  python 02-a2ui/3-open-ended/server.py   then open http://localhost:8000
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import a2ui_messages as a2ui  # noqa: E402
from shared import llm  # noqa: E402
from shared.agui import create_app, last_user_text, serve, stream_run, text_message  # noqa: E402

SURFACE = "trip"

SYSTEM = """You build small interactive widgets for a trip-planning web app.
Reply with ONLY an HTML fragment (no markdown, no code fences, no <html> or <head>).
Inline all CSS in one <style> tag and all JavaScript in one <script> tag.
It runs in a sandbox with NO network: no external scripts, fonts, images or fetch().
Use a clean, modern look on a white background, fit in about 700x450 pixels, and make
at least one thing interactive (tabs, a checklist, a slider, a toggle...).
Use realistic example data; budgets are estimates."""

OFFLINE_REPLY = (HERE / "offline_reply.html").read_text()

app = create_app(HERE, mounts={"/a2ui": HERE.parent / "web"})


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        yield from text_message("The model is writing raw HTML…")
        started = time.perf_counter()
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        html = llm.strip_fences("".join(llm.stream(messages, fake=OFFLINE_REPLY)))
        seconds = time.perf_counter() - started

        components = [{"id": "root", "component": "HtmlFrame", "html": html, "height": 480}]
        update = a2ui.update_components(SURFACE, components)
        errors = a2ui.validate(update, allow_html=True)
        if errors:
            raise ValueError("; ".join(errors))
        yield from a2ui.as_agui([a2ui.create_surface(SURFACE, a2ui.TRIP_CATALOG_ID), update])
        yield from text_message(
            f" {len(html):,} characters of HTML in {seconds:.1f}s, delivered as ONE custom A2UI component "
            "(catalog: Basic + HtmlFrame). A2UI cannot validate what is inside it, so it runs in a sandbox."
        )

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
