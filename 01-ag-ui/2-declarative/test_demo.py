import json

from shared.catalog import validate_spec
from shared.testing import load_server, run

server = load_server(__file__)


def test_spec_arrives_as_state_snapshot():
    events = run(server.app, "Plan 3 days in Tokyo")
    snapshot = next(e for e in events if e["type"] == "STATE_SNAPSHOT")["snapshot"]
    assert validate_spec(snapshot["ui"]) == []


def test_correction_loop_fixes_a_bad_spec(monkeypatch):
    bad = {"root": "a", "elements": {"a": {"type": "Carousel", "props": {}}}}  # not in the catalog
    good = json.loads(server.OFFLINE_REPLY)
    replies = iter([json.dumps(bad), json.dumps(good)])
    monkeypatch.setattr(server.llm, "chat", lambda *a, **k: {"text": next(replies), "tool_calls": []})

    events = run(server.app, "Plan 3 days in Tokyo")
    checks = [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "validation"]
    assert checks[0]["errors"] and checks[1]["errors"] == []
    assert any(e["type"] == "STATE_SNAPSHOT" for e in events)


def test_gives_up_with_run_error(monkeypatch):
    monkeypatch.setattr(server.llm, "chat", lambda *a, **k: {"text": "not json", "tool_calls": []})
    events = run(server.app, "x")
    assert events[-1]["type"] == "RUN_ERROR"
