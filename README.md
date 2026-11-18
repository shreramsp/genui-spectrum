# genui-spectrum

Generative UI across the spectrum: static, declarative, open-ended and mixed-mode agent interfaces with **AG-UI**, **A2UI**, **OpenUI**, **json-render** and **MCP Apps**, plus harness integration. 24 runnable codelabs, each with a code walkthrough and offline tests.

> CMPE-297 Sec 49 (Special Topics, GenUX), Fall 2026, Assignment 4
> Reference: [dlmastery/simple-coding-harness/genui](https://github.com/dlmastery/simple-coding-harness/tree/main/genui)

## The idea in one picture

```
           how much does the MODEL decide?
  static ──────── declarative ──────── open-ended        mixed = declarative + one open-ended region
  picks a         arranges parts       writes its own
  ready-made      from a catalog       HTML/JS (sandboxed)
  component       (validated)
```

Every codelab is the **same trip-planner app** ("Plan 3 days in Tokyo"), so the only thing that changes between demos is the technology or the mode.

## The six parts

The parts build on each other:

| # | Part | Role | Static | Declarative | Open-ended | Mixed |
|---|---|---|---|---|---|---|
| 01 | [AG-UI](01-ag-ui/) | The **pipe**: agent → page events | ✅ | ✅ | ✅ | ✅ |
| 02 | [A2UI](02-a2ui/) | A UI **format** sent through the pipe | ✅ | ✅ | ✅ | ✅ |
| 03 | [OpenUI](03-openui/) | A compact UI **language** | ✅ | ✅ | ✅ | ✅ |
| 04 | [json-render](04-json-render/) | One spec, several **renderers** | ✅ | ✅ | ✅ | ✅ |
| 05 | [MCP Apps](05-mcp-apps/) | The UI hosted inside **another app** | ✅ | ✅ | ✅ | ✅ |
| 06 | [Harness integration](06-harness-integration/) | All of it in a real **agent loop** | ✅ | ✅ | ✅ | ✅ |

Each part folder has a `README.md`: what the technology is, a walkthrough of each mode's code, screenshots, and check-your-understanding questions.

### How each technology does each mode

| | Static | Declarative | Open-ended | Mixed (+ actions) |
|---|---|---|---|---|
| **AG-UI** | Pre-built components = tools (`TOOL_CALL_*`) | Spec in shared state (`STATE_SNAPSHOT`) | HTML in a `CUSTOM` event | Clicks → allow-list → `STATE_DELTA` |
| **A2UI** | Hand-written components, model writes the **data model** | Model writes components, checked by the official v0.9.1 schema | Custom catalog component `HtmlFrame` | Upsert changed components by id + new data |
| **OpenUI** | Hand-written OpenUI Lang template | Model writes OpenUI Lang, rendered **while streaming** | HTML streamed inside an `HtmlArtifact` | Resend changed statements, `mergeStatements()` |
| **json-render** | Hand-written spec, model writes the **state** | Model streams **JSONL patches** | `HtmlFrame` catalog entry | Actions declared **in the catalog**, patch-only updates |
| **MCP Apps** | Hand-written `ui://` view | Server's model designs the spec | **Nested** sandbox in the view | View calls an app-only tool through the host |
| **Harness** | Agent picks a pre-built view after reading files | `render_ui` tool; errors come back as tool results | `render_html` tool | Clicks continue the same agent conversation |

## Repository layout

```
shared/                   written once, used by every part
  llm.py                  Gemini (OpenAI-compatible API) + offline replay + the $ spending cap
  agui.py                 AG-UI events, SSE streaming, the demo web app
  catalog.py              the shared component catalog: prompt text + validator + action allow-list
  correct.py              the correction loop (errors go back to the model)
  patch.py, terminal.py   JSON Patch diff/apply; a terminal renderer for specs
  web/                    browser: AG-UI client, catalog renderer, sandbox, page shell, styles
  check_all.py            runs every test and opens every demo in a headless browser
01-ag-ui/ … 06-harness-integration/
  README.md               the part's walkthrough
  1-static/ 2-declarative/ 3-open-ended/ 4-mixed/
     server.py            start this demo (FastAPI), then open http://localhost:8000
     app.js, index.html   the page
     offline_*            saved model replies, used when there is no API key
     test_demo.py         offline tests
     screenshot*.png      example output
```

## Setup (once)

Needs Python 3.13 and Node.js 22+ (Node is used by Parts 03 and 04 to run the real OpenUI and json-render parsers).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your Gemini key into .env (GEMINI_API_KEY=...)
python shared/llm.py          # prints the model, a test reply, and the spend so far
```

Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). The default model is `gemini-3.1-flash-lite`, the cheapest stable one. `.env` is git-ignored.

**No key?** Everything still runs **offline**: each demo replays its saved model replies.

### Spending cap

Every live Gemini call goes through [shared/llm.py](shared/llm.py). Before each call it adds that call's **worst-case** cost to the spend so far (tracked in `.gemini_spend.json`). If the total could pass `SPEND_LIMIT_USD` (default **$0.20**, in `.env`), no request is sent. Only you can raise the limit. Testing all six parts live used about $0.007.

## Run

```bash
python 02-a2ui/4-mixed/server.py       # any demo: then open http://localhost:8000
pytest                                 # all offline tests
python shared/check_all.py             # every test + every demo in a headless browser
python 06-harness-integration/harness.py --mode declarative "Summarize my trip spending"   # the agent in the terminal
```

Tips: `PORT=8001 python …` runs a second demo at the same time. `OFFLINE=1` forces offline mode even with a key. `OFFLINE_STREAM_DELAY=0.05` makes offline replies stream slowly, so you can watch progressive rendering. Every finished part is tagged (`git tag`): `git checkout part-03-openui` brings back that version, `git checkout main` returns.
