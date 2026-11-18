"""01 AG-UI · 3 OPEN-ENDED — the agent writes the UI itself, as raw HTML/CSS/JS.

New compared with 2-declarative:
  * No catalog. The model can draw anything: a timeline, a map-like grid, a quiz...
  * Because we cannot validate free-form code against a catalog, the page runs it in a
    SANDBOXED IFRAME (no cookies, no network, no access to our page). See shared/web/sandbox.js.
  * The HTML travels as an AG-UI CUSTOM event, because it is app-specific data.
  * We report size and time: freedom costs tokens and seconds compared with a small spec.

Run:  python 01-ag-ui/3-open-ended/server.py   then open http://localhost:8000
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from ag_ui.core import RunAgentInput  # noqa: E402

from shared import llm  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402

SYSTEM = """You build small interactive widgets for a trip-planning web app.
Reply with ONLY an HTML fragment (no markdown, no code fences, no <html> or <head>).
Inline all CSS in one <style> tag and all JavaScript in one <script> tag.
It runs in a sandbox with NO network: no external scripts, fonts, images or fetch().
Use a clean, modern look on a white background, fit in about 700x450 pixels, and make
at least one thing interactive (tabs, a checklist, a slider, a toggle...).
Use realistic example data; budgets are estimates."""

OFFLINE_REPLY = (HERE / "offline_reply.html").read_text()

app = create_app(HERE)


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        yield from text_message("Writing a custom UI from scratch…")
        started = time.perf_counter()
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": last_user_text(run_input)}]
        html = llm.strip_fences("".join(llm.stream(messages, fake=OFFLINE_REPLY)))
        seconds = time.perf_counter() - started

        yield custom("html_ui", {"html": html})
        yield from text_message(
            f" Generated {len(html):,} characters of HTML in {seconds:.1f}s. "
            "It runs in a sandboxed iframe, because no catalog can check free-form code."
        )

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
