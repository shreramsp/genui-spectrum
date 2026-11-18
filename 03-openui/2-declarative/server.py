"""03 OpenUI · 2 DECLARATIVE — the model writes OpenUI Lang itself, streamed to the page live.

New compared with 1-static:
  * The system prompt is GENERATED from the catalog by OpenUI (library.prompt() in
    web/prompt.mjs -> web/prompt.txt). One Zod definition = prompt + validator + renderer.
  * The model's text streams to the page as it is written. <Renderer> re-parses after every
    piece: `root = Stack([title, plan])` appears first, and `title`/`plan` fill in as their
    lines arrive. That is OpenUI Lang's "forward reference" trick for progressive UI.
  * When the stream ends, the server checks the program with the REAL OpenUI parser
    (unknown components, missing references, wrong argument types). If it is wrong, the
    page is reset and the errors go back to the model for one more try.

Run:  python 03-openui/2-declarative/server.py   then open http://localhost:8000
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import openui_tools as openui  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402

OFFLINE_REPLY = (HERE / "offline_reply.oui").read_text()
MAX_ATTEMPTS = 2

app = create_app(HERE, mounts={"/openui": HERE.parent / "web"})


@app.post("/agent")
def agent(run_input: RunAgentInput):
    def body():
        messages = [{"role": "system", "content": openui.PROMPT}, {"role": "user", "content": last_user_text(run_input)}]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                yield openui.reset()
            program = yield from openui.stream_program(messages, OFFLINE_REPLY)
            result = openui.check(program)
            yield custom("validation", {"attempt": attempt, "errors": result["errors"]})
            if not result["errors"]:
                yield from text_message(
                    f"{result['statementCount']} statements, {len(program):,} characters of OpenUI Lang, checked by the OpenUI parser."
                )
                return
            messages += [
                {"role": "assistant", "content": program},
                {"role": "user", "content": "The OpenUI parser rejected this:\n- " + "\n- ".join(result["errors"]) + "\nReturn the whole corrected program."},
            ]
        raise ValueError("no valid program: " + "; ".join(result["errors"]))

    return stream_run(run_input, body)


if __name__ == "__main__":
    serve(app)
