import json

from shared.testing import load_server, run

server = load_server(__file__)


def jr_events(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "jsonrender"]


def test_patches_build_a_valid_spec_with_state_and_repeat():
    events = run(server.app, "Plan 3 days in Tokyo")
    lines = [v["line"] for v in jr_events(events) if "line" in v]
    paths = [json.loads(line)["path"] for line in lines]
    assert paths[0] == "/root" and paths[-1] == "/state/trip/days/2"   # elements first, days last
    result = server.jr.check("\n".join(lines))
    assert result["errors"] == []


def test_terminal_renderer_resolves_state_and_repeat():
    events = run(server.app, "Plan 3 days in Tokyo")
    term = next(v["terminal"] for v in jr_events(events) if "terminal" in v)
    assert "3 days in Tokyo" in term and "Day 3 · Tsukiji" in term and "█" in term
