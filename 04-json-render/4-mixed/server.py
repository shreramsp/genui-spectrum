"""04 json-render · 4 MIXED — catalog components + ONE HtmlFrame, with CATALOG ACTIONS and patches.

Combines 2-declarative (streamed JSONL patches, catalog validation) with 3-open-ended (one
HtmlFrame in the sandbox). What json-render adds: the ACTIONS are part of the catalog
(web/catalog.mjs: cheaper, set_pace). A Button binds to one with
    "on": {"press": {"action": "cheaper", "params": {}}}
and the checker rejects any action the catalog does not declare, so the model is told up
front which actions exist.

A click (catalog Button or sendAction() in the HtmlFrame):
  -> new run with forwardedProps {action, params}
  -> the server checks it against the actions in ITS OWN copy of the spec
  -> the model replies with ONLY the JSONL patches that change the spec
  -> the server compiles them onto its copy, validates, forwards just those lines;
     the page's stream compiler applies them on top of what it already has.

Run:  python 04-json-render/4-mixed/server.py   then open http://localhost:8000
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import jr_tools as jr  # noqa: E402
from shared import llm  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402

OFFLINE_FIRST = (HERE / "offline_reply.jsonl").read_text()
OFFLINE_PATCH = (HERE / "offline_patch.jsonl").read_text()
MAX_ATTEMPTS = 2

SESSIONS = {}  # thread_id -> {"request", "spec"}. The server's trusted copy.

app = create_app(HERE, mounts={"/jr": HERE.parent / "web"})


def screen_errors(result):
    errors = list(result["errors"])
    frames = result["types"].count("HtmlFrame")
    if frames != 1:
        errors.append(f"use exactly one HtmlFrame (found {frames})")
    if "cheaper" not in result["actions"]:
        errors.append('add a Button bound to the "cheaper" action')
    return errors


def check(jsonl, base=None):
    return jr.check(jsonl, base=base, allow_html=True, with_actions=True)


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action, params = jr.action_from(run_input)
    session = SESSIONS.get(run_input.thread_id)

    def first_turn():
        request = last_user_text(run_input)
        messages = [{"role": "system", "content": jr.PROMPT_MIXED}, {"role": "user", "content": request}]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            yield jr.reset()
            jsonl = yield from jr.stream_patches(messages, OFFLINE_FIRST)
            result = check(jsonl)
            errors = screen_errors(result)
            yield custom("validation", {"attempt": attempt, "errors": errors})
            if not errors:
                SESSIONS[run_input.thread_id] = {"request": request, "spec": result["spec"]}
                yield jr.terminal(result["spec"])
                yield from text_message(f"Done. Catalog actions on this screen: {', '.join(result['actions'])}.")
                return
            messages += [
                {"role": "assistant", "content": jsonl},
                {"role": "user", "content": "Rejected:\n- " + "\n- ".join(errors) + "\nStream the whole corrected spec again."},
            ]
        raise ValueError("no valid spec: " + "; ".join(errors))

    def action_turn():
        allowed = check("", base=session["spec"])["actions"]
        if action not in allowed:  # a click is a request, not a permission
            yield custom("action_blocked", {"action": action, "allowed": allowed})
            yield from text_message(f'Blocked: "{action}" is not an action this screen offers.')
            return
        yield from text_message(f'Handling catalog action "{action}"…')
        messages = [
            {"role": "system", "content": jr.PROMPT_MIXED},
            {
                "role": "user",
                "content": f"Original request: {session['request']}\nCurrent spec:\n{json.dumps(session['spec'])}\n"
                f'The user triggered action "{action}" with params {json.dumps(params)}. Reply with ONLY the JSONL '
                "patches (add/replace/remove) that change the current spec. Do not resend unchanged elements.",
            },
        ]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            reply = llm.strip_fences(llm.chat(messages, fake=OFFLINE_PATCH)["text"])
            jsonl = "\n".join(line for line in reply.splitlines() if line.strip().startswith("{"))
            result = check(jsonl, base=session["spec"])
            errors = screen_errors(result)
            yield custom("validation", {"attempt": attempt, "errors": errors})
            if not errors:
                session["spec"] = result["spec"]
                for patch in jsonl.splitlines():
                    yield jr.line(patch)
                yield jr.terminal(result["spec"])
                yield from text_message(f" Applied {result['patches']} patch(es) on top of the current spec.")
                return
            messages += [
                {"role": "assistant", "content": jsonl},
                {"role": "user", "content": "After applying your patches, json-render found:\n- " + "\n- ".join(errors) + "\nSend corrected patches only."},
            ]
        raise ValueError("no valid patches: " + "; ".join(errors))

    def expired():
        yield from text_message("That screen came from an earlier server session. Please run your request again.")

    if action:
        return stream_run(run_input, action_turn if session else expired)
    return stream_run(run_input, first_turn)


if __name__ == "__main__":
    serve(app)
