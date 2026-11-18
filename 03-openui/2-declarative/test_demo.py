from shared import llm
from shared.testing import load_server, run

server = load_server(__file__)


def openui_events(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "openui"]


def test_offline_program_is_valid_openui():
    assert server.openui.check(server.OFFLINE_REPLY)["errors"] == []


def test_program_streams_in_many_pieces_and_passes_the_parser():
    events = run(server.app, "Plan 3 days in Tokyo")
    pieces = openui_events(events)
    assert len(pieces) > 5
    assert "".join(p["delta"] for p in pieces).startswith("root = Stack(")
    check = next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "validation")
    assert check["errors"] == []


def test_bad_program_triggers_reset_and_retry(monkeypatch):
    replies = iter(["root = Stack([a, b])\na = Carousel(1)", server.OFFLINE_REPLY])
    monkeypatch.setattr(llm, "stream", lambda *a, **k: iter([next(replies)]))
    events = run(server.app, "x")
    checks = [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "validation"]
    assert checks[0]["errors"] and checks[1]["errors"] == []
    assert {"reset": True} in openui_events(events)


def test_htmlartifact_is_rejected_in_declarative_mode():
    bad = 'root = Stack([a])\na = HtmlArtifact("x", "<p>hi</p>")'
    assert server.openui.check(bad)["errors"]
