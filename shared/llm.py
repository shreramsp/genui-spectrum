"""The ONE place that talks to the model.

Gemini understands the OpenAI "chat completions" format at a special URL, so we
use the standard `openai` Python package and simply point it at Google.

Offline mode
------------
If there is no GEMINI_API_KEY (or OFFLINE=1 is set), no request is sent. Every
call returns the `fake` reply the caller passes in instead. Tests and first runs
therefore need no key and cost nothing.

Spending cap
------------
Every live call is priced from the token usage Google reports and added to
.gemini_spend.json (git-ignored). BEFORE each call we add the call's WORST-CASE
cost (whole prompt + the maximum allowed output). If that could pass
SPEND_LIMIT_USD (default $0.20), the call is refused. So the cap cannot be
overshot, and only a human raising the number in .env lets calls continue.
"""

import json
import math
import os
import re
import time
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

# ---------------- spending cap ----------------
SPEND_LIMIT_USD = float(os.environ.get("SPEND_LIMIT_USD", "0.20"))
LEDGER = ROOT / ".gemini_spend.json"
MAX_OUTPUT_TOKENS = 8192  # no single reply may be longer than this

# USD per 1M tokens (input, output). Unknown models get a deliberately HIGH price so the cap stays safe.
PRICES = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),
}
PRICE_IN, PRICE_OUT = PRICES.get(MODEL, (2.00, 12.00))


class BudgetExceeded(RuntimeError):
    pass


def spent():
    try:
        return json.loads(LEDGER.read_text())["spent_usd"]
    except (FileNotFoundError, KeyError, ValueError):
        return 0.0


def _record(prompt_tokens, output_tokens):
    data = {"spent_usd": 0.0, "calls": 0, "prompt_tokens": 0, "output_tokens": 0}
    try:
        data.update(json.loads(LEDGER.read_text()))
    except (FileNotFoundError, ValueError):
        pass
    cost = (prompt_tokens * PRICE_IN + output_tokens * PRICE_OUT) / 1_000_000
    data["spent_usd"] = round(data["spent_usd"] + cost, 6)
    data["calls"] += 1
    data["prompt_tokens"] += prompt_tokens
    data["output_tokens"] += output_tokens
    LEDGER.write_text(json.dumps(data, indent=2))


def _estimate_tokens(messages, tools=None):
    text = json.dumps(messages) + (json.dumps(tools) if tools else "")
    return math.ceil(len(text) / 3)  # generous: real tokens are usually ~len/4


def _check_budget(messages, tools=None):
    worst = (_estimate_tokens(messages, tools) * PRICE_IN + MAX_OUTPUT_TOKENS * PRICE_OUT) / 1_000_000
    if spent() + worst > SPEND_LIMIT_USD:
        raise BudgetExceeded(
            f"Gemini spending cap reached: ${spent():.4f} spent of ${SPEND_LIMIT_USD:.2f} "
            f"(this call could cost up to ${worst:.4f}). No request was sent. "
            "To allow more, raise SPEND_LIMIT_USD in .env."
        )


def _record_usage(usage, messages, tools, output_text):
    """Prefer Google's own token counts. total - prompt includes any hidden 'thinking' tokens."""
    if usage is not None and usage.prompt_tokens is not None:
        prompt = usage.prompt_tokens
        output = max((usage.total_tokens or 0) - prompt, usage.completion_tokens or 0)
    else:  # no usage reported: estimate generously
        prompt, output = _estimate_tokens(messages, tools), math.ceil(len(output_text) / 3) + 1
    _record(prompt, output)


# ---------------- calls ----------------
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

    _check_budget(messages, tools)
    request = {"model": MODEL, "messages": messages, "max_tokens": MAX_OUTPUT_TOKENS}
    if tools:
        request["tools"] = tools
    if json_mode:
        request["response_format"] = {"type": "json_object"}

    response = _get_client().chat.completions.create(**request)
    reply = response.choices[0].message
    _record_usage(response.usage, messages, tools, (reply.content or "") + str(reply.tool_calls or ""))
    calls = [
        {"id": c.id or f"call_{i}", "name": c.function.name, "arguments": json.loads(c.function.arguments or "{}")}
        for i, c in enumerate(reply.tool_calls or [])
    ]
    return {"text": reply.content or "", "tool_calls": calls}


def stream(messages, fake=None):
    """Send one request and yield the reply text piece by piece as it arrives."""
    if OFFLINE:
        text = fake or ""
        delay = float(os.environ.get("OFFLINE_STREAM_DELAY", "0"))  # e.g. 0.05 to watch it stream
        for i in range(0, len(text), 60):  # pretend to stream the canned reply
            if delay:
                time.sleep(delay)
            yield text[i : i + 60]
        return

    _check_budget(messages)
    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=MAX_OUTPUT_TOKENS,
        stream=True,
        stream_options={"include_usage": True},
    )
    usage, text = None, ""
    try:
        for chunk in response:
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                text += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content
    finally:  # recorded even if the caller stops reading early
        _record_usage(usage, messages, None, text)


def strip_fences(text):
    """Models often wrap output in ```json ... ``` or ```html ... ```. Remove that wrapper."""
    match = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def parse_json(text):
    """Parse a JSON reply, tolerating code fences around it."""
    return json.loads(strip_fences(text))


if __name__ == "__main__":
    # Quick check: python shared/llm.py
    print(f"model={MODEL} offline={OFFLINE} spent=${spent():.4f} of ${SPEND_LIMIT_USD:.2f}")
    print(chat([{"role": "user", "content": "Say hello in five words."}], fake="(offline) hello from the fake model")["text"])
    if not OFFLINE:
        print(f"spent after this call: ${spent():.6f}")
