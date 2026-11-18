"""The correction loop, shared by every part from 02 on (01 writes it out by hand to teach it).

Ask the model for JSON, check it, and if the check finds problems, send the errors back
as a new message and ask again. Each attempt is reported to the page as a CUSTOM
"validation" event, so you can watch the loop in the event log.
"""

import json

from shared import llm
from shared.agui import custom


def ask_until_valid(messages, check, fake, attempts=2):
    """Generator: yields AG-UI events, then RETURNS the first reply that passes `check`.

    `check(data)` returns a list of error strings (empty = valid).
    Use it as:  data = yield from ask_until_valid(...)
    """
    errors = []
    for attempt in range(1, attempts + 1):
        reply = llm.chat(messages, json_mode=True, fake=fake)["text"]
        try:
            data = llm.parse_json(reply)
            errors = check(data)
        except json.JSONDecodeError as exc:
            errors = [f"not valid JSON: {exc}"]
        yield custom("validation", {"attempt": attempt, "errors": errors[:10]})
        if not errors:
            return data
        messages = messages + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "Rejected:\n- " + "\n- ".join(errors[:10]) + "\nReturn the corrected JSON only."},
        ]
    raise ValueError("model could not produce a valid reply: " + "; ".join(errors[:5]))
