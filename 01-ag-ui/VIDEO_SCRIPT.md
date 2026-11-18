# Video script · Part 01: AG-UI (about 10–12 minutes)

Talking points, not a script to read out. Say them in your own words. **Bold** = something to do on screen.

**Before recording:** put your key in `.env`, then run `source .venv/bin/activate`. Open VS Code with the repo on the left and the browser on the right. Close other tabs. Make the fonts larger (VS Code: Cmd + `+`).

---

## 0 · Intro (1 min)
- "This is part 1 of my GenUI assignment: AG-UI."
- **Show the root README table.** Six technologies × four modes. They all use the same trip-planner app, so only one thing changes at a time.
- AG-UI is the *pipe*: a standard stream of events from agent to page. **Show the event table in `01-ag-ui/README.md`.**
- **Show `shared/`.** It's written once and reused everywhere: `llm.py` (Gemini), `agui.py` (events), `catalog.py`, and `web/` (renderer, sandbox).

## 1 · Static (2.5 min)
- **Open `1-static/server.py` and scroll to `TOOLS`.** "Each tool is a component that already exists on the page. To the model, it's just a function."
- **Scroll to `agent()`.** One model call; then text goes out as `text_message` and each tool call as `tool_call`.
- **Open `shared/agui.py` → `tool_call()`.** START, then the JSON args in pieces, then END.
- **Open `1-static/app.js` → `COMPONENTS`.** Hand-written by me, not the model.
- **Terminal:** `python 01-ag-ui/1-static/server.py` → **browser** → **Run**.
- **Point at the event log:** RUN_STARTED → TEXT → TOOL_CALL_START *show_itinerary* → ARGS… → END → card appears. **Expand one TOOL_CALL_ARGS** to show the JSON arrives in pieces.
- **Try "What should I pack for Iceland?"** The model picks a *different* component.
- Key line: *"The model chooses which component and what data. It never decides the layout."*

## 2 · Declarative (2.5 min)
- **Open `shared/catalog.py`.** One catalog, three jobs: prompt, validator, renderer registry. Show `validate_spec`.
- **Open `2-declarative/server.py` → `SYSTEM`.** The catalog is pasted into the prompt.
- **`design_ui()`:** validate → if errors, send them back to the model → retry once. "Errors are just another message."
- **Run it.** Point at `CUSTOM validation` (attempt 1, errors: []) and then `STATE_SNAPSHOT`. **Expand the snapshot** to show the flat `elements` map.
- **Open `shared/web/render.js`.** One function per component name, nothing else can be drawn, and it uses `textContent` (no HTML injection).
- **Try a different prompt** ("Compare Lisbon and Barcelona"). A totally different layout from the same catalog.
- Optional: **`pytest 01-ag-ui/2-declarative -v`** shows `test_correction_loop_fixes_a_bad_spec`.

## 3 · Open-ended (2 min)
- **`3-open-ended/server.py` → `SYSTEM`.** No catalog; the model writes HTML/CSS/JS.
- **Run it.** The HTML arrives as one `CUSTOM html_ui` event. **Read the size/time message**: compare it with the small declarative spec.
- **Open `shared/web/sandbox.js`** and explain the three layers: no `allow-same-origin`, CSP `default-src 'none'`, and only `sendAction` out.
- **Interact with the generated widget** (tabs, checkboxes).
- Optional demo: **right-click the iframe → Inspect → Console**, then type `fetch("https://example.com")`. It's blocked by the CSP.
- Trade-off: maximum freedom, but no validation, more tokens, and an inconsistent style.

## 4 · Mixed (2.5 min)
- "The recommended default: catalog for the standard parts, one sandboxed region for the special part."
- **Run it.** Point out the pink **AI-generated region** among normal catalog components.
- **Move the slider, then click "Apply this pace"** inside the sandbox. Event log: new run, `STATE_DELTA` with only a few ops. **Expand it.**
- **Click "Make it cheaper"** (a catalog button). Same flow.
- **`4-mixed/server.py`:** `SESSIONS` is the server's own copy. `actions_in()` is the allow-list. Show `action_blocked`. "A click is a request, not a permission."
- **`shared/patch.py` → `diff_spec`.** Only the changed elements are sent.

## 5 · Tests and wrap-up (1 min)
- **`pytest 01-ag-ui -v`**: 13 tests, offline, no key needed (they replay saved model replies).
- Summary: *same pipe (AG-UI), four amounts of model freedom.* Next part: A2UI, a dedicated UI *format* that rides on this pipe.
