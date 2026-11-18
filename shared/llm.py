"""The ONE place that talks to the model.

Gemini understands the OpenAI "chat completions" format at a special URL, so we
use the standard `openai` Python package and simply point it at Google.

Offline mode
------------
If there is no GEMINI_API_KEY (or OFFLINE=1 is set), no request is sent. Every
call returns the `fake` reply the caller passes in instead. Tests and first runs
therefore need no key and cost nothing.
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Read KEY=VALUE lines from the repo's .env file (never committed)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL", "gemini-3.1-flash-lite")
BASE_URL = os.environ.get("BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
OFFLINE = os.environ.get("OFFLINE") == "1" or not API_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


def chat(messages, tools=None, json_mode=False, fake=None):
    """Send one request and wait for the whole reply.

    Returns {"text": str, "tool_calls": [{"id", "name", "arguments": dict}]}.
    `fake` is what offline mode returns: a string (plain text) or that same dict.
    """
    if OFFLINE:
        if fake is None:
            raise RuntimeError("Offline mode (no GEMINI_API_KEY) and no fake reply was given.")
        return {"text": fake, "tool_calls": []} if isinstance(fake, str) else fake

    request = {"model": MODEL, "messages": messages}
    if tools:
        request["tools"] = tools
    if json_mode:
        request["response_format"] = {"type": "json_object"}

    reply = _get_client().chat.completions.create(**request).choices[0].message
    calls = [
        {"id": c.id or f"call_{i}", "name": c.function.name, "arguments": json.loads(c.function.arguments or "{}")}
        for i, c in enumerate(reply.tool_calls or [])
    ]
    return {"text": reply.content or "", "tool_calls": calls}


def stream(messages, fake=None):
    """Send one request and yield the reply text piece by piece as it arrives."""
    if OFFLINE:
        text = fake or ""
        for i in range(0, len(text), 60):  # pretend to stream the canned reply
            yield text[i : i + 60]
        return

    response = _get_client().chat.completions.create(model=MODEL, messages=messages, stream=True)
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def strip_fences(text):
    """Models often wrap output in ```json ... ``` or ```html ... ```. Remove that wrapper."""
    match = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def parse_json(text):
    """Parse a JSON reply, tolerating code fences around it."""
    return json.loads(strip_fences(text))


if __name__ == "__main__":
    # Quick check: python shared/llm.py
    print(f"model={MODEL} offline={OFFLINE}")
    print(chat([{"role": "user", "content": "Say hello in five words."}], fake="(offline) hello from the fake model")["text"])
