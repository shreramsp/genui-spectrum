import json

from shared.testing import load_server, run

server = load_server(__file__)


def lines_of(events):
    return [e["value"]["line"] for e in events if e["type"] == "CUSTOM" and e["name"] == "jsonrender" and "line" in e["value"]]


def test_first_screen_mixes_catalog_htmlframe_and_actions():
    run(server.app, "Plan 3 days in Tokyo", thread="j1")
    result = server.check("", base=server.SESSIONS["j1"]["spec"])
    assert server.screen_errors(result) == []
    assert set(result["actions"]) == {"cheaper", "set_pace"}


def test_action_sends_only_patches():
    run(server.app, "Plan 3 days in Tokyo", thread="j2")
    events = run(server.app, "[action]", forwarded={"action": "set_pace", "params": {"pace": "relaxed"}}, thread="j2")
    lines = lines_of(events)
    assert len(lines) == 5 and all(json.loads(x)["op"] in ("add", "replace") for x in lines)
    assert server.SESSIONS["j2"]["spec"]["elements"]["metric-2"]["props"]["value"] == "$455"


def test_unknown_action_is_blocked():
    run(server.app, "Plan 3 days in Tokyo", thread="j3")
    events = run(server.app, "[action]", forwarded={"action": "book_flight"}, thread="j3")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
    assert not lines_of(events)


def test_actions_outside_the_catalog_are_rejected():
    bad = server.OFFLINE_FIRST.replace('"action": "cheaper"', '"action": "delete_account"')
    assert any("not in the catalog" in e for e in server.check(bad)["errors"])
