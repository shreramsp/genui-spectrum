import json

from shared.testing import load_server, run

server = load_server(__file__)
a2ui = server.a2ui


def a2ui_msgs(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "a2ui"]


def test_first_screen_has_basic_components_and_one_htmlframe():
    msgs = a2ui_msgs(run(server.app, "Plan 3 days in Tokyo", thread="m1"))
    components = msgs[1]["updateComponents"]["components"]
    kinds = [c["component"] for c in components]
    assert kinds.count("HtmlFrame") == 1 and "Text" in kinds
    assert a2ui.actions_in(components) == {"cheaper", "set_pace"}


def test_action_resends_only_changed_components():
    run(server.app, "Plan 3 days in Tokyo", thread="m2")
    action = {"name": "set_pace", "surfaceId": "trip", "sourceComponentId": "pace", "context": {"pace": "relaxed"}}
    msgs = a2ui_msgs(run(server.app, "[action]", forwarded={"a2uiAction": action}, thread="m2"))
    assert [list(m)[1] for m in msgs] == ["updateComponents", "updateDataModel"]
    assert {c["id"] for c in msgs[0]["updateComponents"]["components"]} == {"main", "note"}


def test_unknown_action_is_blocked():
    run(server.app, "Plan 3 days in Tokyo", thread="m3")
    events = run(server.app, "[action]", forwarded={"a2uiAction": {"name": "book_flight", "context": {}}}, thread="m3")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
    assert not a2ui_msgs(events)


def test_zero_or_two_htmlframes_rejected():
    reply = json.loads(server.OFFLINE_FIRST)
    no_frame = [c for c in reply["components"] if c["component"] != "HtmlFrame"]
    assert any("exactly one HtmlFrame" in e for e in server.screen_errors(no_frame, {}))
