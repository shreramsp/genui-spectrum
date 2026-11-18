from shared import llm
from shared.testing import load_server, run

server = load_server(__file__)


def jr_events(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "jsonrender"]


def test_offline_spec_is_valid():
    assert server.jr.check(server.OFFLINE_REPLY)["errors"] == []


def test_each_patch_is_forwarded_as_its_own_event():
    events = run(server.app, "Plan 3 days in Tokyo")
    lines = [v["line"] for v in jr_events(events) if "line" in v]
    assert len(lines) == len(server.OFFLINE_REPLY.strip().splitlines())
    assert any("terminal" in v for v in jr_events(events))


def test_fences_and_prose_are_dropped_while_streaming(monkeypatch):
    noisy = "Here you go:\n```jsonl\n" + server.OFFLINE_REPLY + "```\n"
    monkeypatch.setattr(llm, "stream", lambda *a, **k: iter([noisy[i : i + 50] for i in range(0, len(noisy), 50)]))
    events = run(server.app, "x")
    lines = [v["line"] for v in jr_events(events) if "line" in v]
    assert all(line.startswith("{") for line in lines)
    assert next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "validation")["errors"] == []


def test_unknown_component_triggers_retry(monkeypatch):
    bad = '{"op":"add","path":"/root","value":"a"}\n{"op":"add","path":"/elements/a","value":{"type":"Carousel","props":{},"children":[]}}'
    replies = iter([bad, server.OFFLINE_REPLY])
    monkeypatch.setattr(llm, "stream", lambda *a, **k: iter([next(replies)]))
    checks = [e["value"] for e in run(server.app, "x") if e["type"] == "CUSTOM" and e["name"] == "validation"]
    assert checks[0]["errors"] and checks[1]["errors"] == []
