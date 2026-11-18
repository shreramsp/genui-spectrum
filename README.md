# genui-spectrum

Generative UI across the spectrum: static, declarative, open-ended and mixed-mode agent interfaces with **AG-UI**, **A2UI**, **OpenUI**, **json-render** and **MCP Apps**, plus harness integration. Runnable codelabs with video walkthroughs.

> CMPE-297 Sec 49 (Special Topics, GenUX), Fall 2026, Assignment 4
> Reference: [dlmastery/simple-coding-harness/genui](https://github.com/dlmastery/simple-coding-harness/tree/main/genui)

## The idea in one picture

```
           how much does the MODEL decide?
  static ──────── declarative ──────── open-ended        mixed = declarative + one open-ended region
  picks a         arranges parts       writes its own
  ready-made      from a catalog       HTML/JS (sandboxed)
  component       (validated JSON)
```

Every codelab is the **same trip-planner app** ("Plan 3 days in Tokyo"), so the only thing that changes between demos is the technology or the mode.

## Build order

The parts build on each other:

| # | Part | Role | Static | Declarative | Open-ended | Mixed | Video |
|---|---|---|---|---|---|---|---|
| 01 | [AG-UI](01-ag-ui/) | The **pipe**: agent → page events | ✅ | ✅ | ✅ | ✅ | _TBD_ |
| 02 | [A2UI](02-a2ui/) | A UI **format** sent through the pipe | ✅ | ✅ | ✅ | ✅ | _TBD_ |
| 03 | [OpenUI](03-openui/) | A compact UI **language** | ⬜ | ⬜ | ⬜ | ⬜ | _TBD_ |
| 04 | [json-render](04-json-render/) | One spec, several **renderers** | ⬜ | ⬜ | ⬜ | ⬜ | _TBD_ |
| 05 | [MCP Apps](05-mcp-apps/) | The UI hosted inside **another app** | ⬜ | ⬜ | ⬜ | ⬜ | _TBD_ |
| 06 | [Harness integration](06-harness-integration/) | All of it in a real **agent loop** | ⬜ | ⬜ | ⬜ | ⬜ | _TBD_ |

Each part folder has a `README.md` (code walkthrough with screenshots) and a `VIDEO_SCRIPT.md`.

## Repository layout

```
shared/                 written once, used by every demo
  llm.py                talks to Gemini (or replays a saved reply when offline)
  agui.py               AG-UI events + server helpers
  catalog.py            allowed components: prompt text + validator
  patch.py              JSON Patch diff/apply (for STATE_DELTA)
  web/                  browser side: AG-UI client, renderer, sandbox, page shell, styles
01-ag-ui/
  1-static/  2-declarative/  3-open-ended/  4-mixed/
     server.py          the agent (Python, FastAPI)
     app.js             the page logic
     offline_reply.*    the saved model reply used without an API key
     test_demo.py       offline tests
```

## Setup (once)

Needs Python 3.13 and Node.js 22+.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your Gemini key into .env
python shared/llm.py          # prints the model name and a test reply
```

Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). The default model is `gemini-3.1-flash-lite`, the cheapest stable one. `.env` is git-ignored.

**No key?** Everything still runs **offline**: each demo replays its saved `offline_reply.*` file.

## Run

```bash
python 01-ag-ui/1-static/server.py     # open http://localhost:8000
pytest                                 # all offline tests
python shared/screenshot.py 01-ag-ui/1-static   # headless-browser check + screenshot
python shared/check_all.py             # check EVERY demo still works (run before recording)
```

## Recording all the videos at the end

1. `python shared/check_all.py`: confirms every demo, old and new, still runs.
2. Record each part from its `VIDEO_SCRIPT.md`, one server at a time (all use port 8000; use `PORT=8001 python ...` to run two at once).
3. If something ever breaks, every finished part is tagged (`git tag` lists them). `git checkout part-01-ag-ui` brings back exactly the version that worked; `git checkout main` returns.
