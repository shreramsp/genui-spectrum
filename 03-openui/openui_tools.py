"""Python side of Part 03: talk to the OpenUI library (which is JavaScript) and send programs to the page.

OpenUI's parser and catalog live in JavaScript (web/library.mjs). Instead of rewriting them
in Python, the server asks Node:  web/dist/check.mjs  parses a program with the SAME library
the page renders with, and reports errors, components used and actions offered.

The system prompts were generated from the catalog by `npm run build` (web/prompt*.txt).
"""

import json
import subprocess
from pathlib import Path

from shared.agui import custom

WEB = Path(__file__).resolve().parent / "web"
PROMPT = (WEB / "prompt.txt").read_text()
PROMPT_HTML = (WEB / "prompt_html.txt").read_text()


def check(program, allow_html=False, patch=None):
    """Parse with the real OpenUI parser. Returns {program, errors, components, actions, statementCount}.

    With `patch`, OpenUI's mergeStatements() first replaces/adds those statements by name.
    """
    payload = json.dumps({"program": program, "patch": patch, "allowHtml": allow_html})
    out = subprocess.run(["node", str(WEB / "dist" / "check.mjs")], input=payload, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"OpenUI checker failed: {out.stderr[-500:]}")
    return json.loads(out.stdout)


# ---------- AG-UI events the page understands (web/app.mjs) ----------


def delta(text):
    """Append text to the program on the page. The page re-parses after every piece."""
    return custom("openui", {"delta": text})


def reset():
    """Clear the program on the page (before a correction attempt)."""
    return custom("openui", {"reset": True})


def patch(statements):
    """Changed statements only; the page merges them with mergeStatements()."""
    return custom("openui", {"patch": statements})


def stream_lines(program):
    """Send a finished program line by line, so the page shows OpenUI's progressive rendering."""
    for line in program.strip().splitlines(keepends=True):
        yield delta(line if line.endswith("\n") else line + "\n")


def action_from(run_input):
    return (run_input.forwarded_props or {}).get("action"), (run_input.forwarded_props or {}).get("payload")


class FenceFilter:
    """Drop ``` code-fence lines from a stream WITHOUT waiting for the whole reply.

    Text is passed through as soon as we know the current line is not a fence.
    """

    def __init__(self):
        self.line = ""  # start of the current line, held back while it might still be a fence
        self.dropping = False

    def push(self, chunk):
        out = []
        for ch in chunk:
            if self.dropping:
                if ch == "\n":
                    self.dropping = False
                continue
            self.line += ch
            if ch == "\n":
                out.append(self.line)
                self.line = ""
            elif len(self.line) >= 3 or not "```".startswith(self.line.lstrip()):
                if self.line.lstrip().startswith("```"):
                    self.dropping, self.line = True, ""
                else:
                    out.append(self.line)
                    self.line = "\0"  # mark: rest of this line passes straight through
        return "".join(out).replace("\0", "")

    def flush(self):
        rest, self.line = self.line.replace("\0", ""), ""
        return "" if rest.lstrip().startswith("```") else rest


def stream_program(messages, fake, escape=False):
    """Generator: stream the model's reply to the page as it arrives; RETURN the full text.

    escape=True JSON-escapes each piece, for streaming raw HTML inside an OpenUI string literal.
    """
    fence, text = FenceFilter(), ""
    from shared import llm

    for chunk in llm.stream(messages, fake=fake):
        piece = fence.push(chunk)
        if piece:
            text += piece
            yield delta(json.dumps(piece, ensure_ascii=False)[1:-1] if escape else piece)
    piece = fence.flush()
    if piece:
        text += piece
        yield delta(json.dumps(piece, ensure_ascii=False)[1:-1] if escape else piece)
    return text
