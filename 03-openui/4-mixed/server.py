"""03 OpenUI · 4 MIXED — catalog components + ONE HtmlArtifact, with actions and statement patches.

Combines 2-declarative (model-written OpenUI Lang, checked by the real parser) with
3-open-ended (one HtmlArtifact running in the sandbox), then closes the loop:

  click a Button, or sendAction() inside the HtmlArtifact
    -> the page starts a new run with forwardedProps.action
    -> the server checks the name against the actions in ITS OWN copy of the program
    -> the model replies with ONLY the statements that change (same name = replace)
    -> the server merges them with OpenUI's mergeStatements(), checks the result, and sends
       just those statements; the page merges them the same way.

OpenUI's incremental update is "re-send the changed statements by name", the same idea as
A2UI's upsert-by-id in Part 02.

Run:  python 03-openui/4-mixed/server.py   then open http://localhost:8000
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from ag_ui.core import RunAgentInput  # noqa: E402

import openui_tools as openui  # noqa: E402
from shared import llm  # noqa: E402
from shared.agui import create_app, custom, last_user_text, serve, stream_run, text_message  # noqa: E402

OFFLINE_FIRST = (HERE / "offline_reply.oui").read_text()
OFFLINE_PATCH = (HERE / "offline_patch.oui").read_text()
MAX_ATTEMPTS = 2

SESSIONS = {}  # thread_id -> {"request", "program"}. The server's trusted copy.

app = create_app(HERE, mounts={"/openui": HERE.parent / "web"})


def screen_errors(result):
    errors = list(result["errors"])
    if result["components"].count("HtmlArtifact") != 1:
        errors.append(f"use exactly one HtmlArtifact (found {result['components'].count('HtmlArtifact')})")
    if "Button" not in result["components"]:
        errors.append("add one Button with a snake_case action")
    return errors


@app.post("/agent")
def agent(run_input: RunAgentInput):
    action, payload = openui.action_from(run_input)
    session = SESSIONS.get(run_input.thread_id)

    def first_turn():
        request = last_user_text(run_input)
        messages = [{"role": "system", "content": openui.PROMPT_HTML}, {"role": "user", "content": request}]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                yield openui.reset()
            program = yield from openui.stream_program(messages, OFFLINE_FIRST)
            result = openui.check(program, allow_html=True)
            errors = screen_errors(result)
            yield custom("validation", {"attempt": attempt, "errors": errors})
            if not errors:
                SESSIONS[run_input.thread_id] = {"request": request, "program": program}
                yield from text_message(f"Done. Actions on this screen: {', '.join(result['actions'])}.")
                return
            messages += [
                {"role": "assistant", "content": program},
                {"role": "user", "content": "Rejected:\n- " + "\n- ".join(errors) + "\nReturn the whole corrected program."},
            ]
        raise ValueError("no valid program: " + "; ".join(errors))

    def action_turn():
        allowed = openui.check(session["program"], allow_html=True)["actions"]
        if action not in allowed:  # a click is a request, not a permission
            yield custom("action_blocked", {"action": action, "allowed": allowed})
            yield from text_message(f'Blocked: "{action}" is not an action this screen offers.')
            return
        yield from text_message(f'Handling action "{action}"…')
        messages = [
            {"role": "system", "content": openui.PROMPT_HTML},
            {
                "role": "user",
                "content": f"Original request: {session['request']}\nCurrent program:\n{session['program']}\n"
                f'The user triggered action "{action}" with payload {payload}. Reply with ONLY the statements that '
                "change or are new, in OpenUI Lang. A statement with an existing name replaces it. "
                "If you add a statement, also resend the parent that references it.",
            },
        ]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            patch = llm.strip_fences(llm.chat(messages, fake=OFFLINE_PATCH)["text"])
            result = openui.check(session["program"], allow_html=True, patch=patch)
            errors = screen_errors(result)
            yield custom("validation", {"attempt": attempt, "errors": errors})
            if not errors:
                session["program"] = result["program"]
                yield openui.patch(patch)
                yield from text_message(f" Sent {len(patch.strip().splitlines())} changed statement(s); the page merged them.")
                return
            messages += [
                {"role": "assistant", "content": patch},
                {"role": "user", "content": "After merging, the parser found:\n- " + "\n- ".join(errors) + "\nSend corrected statements only."},
            ]
        raise ValueError("no valid patch: " + "; ".join(errors))

    def expired():
        yield from text_message("That screen came from an earlier server session. Please run your request again.")

    if action:
        return stream_run(run_input, action_turn if session else expired)
    return stream_run(run_input, first_turn)


if __name__ == "__main__":
    serve(app)
