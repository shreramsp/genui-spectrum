from shared.testing import load_server, run

server = load_server(__file__)


def openui_events(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "openui"]


def test_first_screen_has_catalog_parts_and_one_htmlartifact():
    run(server.app, "Plan 3 days in Tokyo", thread="o1")
    result = server.openui.check(server.SESSIONS["o1"]["program"], allow_html=True)
    assert server.screen_errors(result) == []
    assert set(result["actions"]) == {"set_pace", "cheaper"}


def test_action_sends_only_changed_statements():
    run(server.app, "Plan 3 days in Tokyo", thread="o2")
    events = run(server.app, "[action]", forwarded={"action": "cheaper"}, thread="o2")
    patches = [v["patch"] for v in openui_events(events) if "patch" in v]
    assert len(patches) == 1 and len(patches[0].strip().splitlines()) == 4
    assert '"$455"' in server.SESSIONS["o2"]["program"] and "note = Text(" in server.SESSIONS["o2"]["program"]


def test_unknown_action_is_blocked():
    run(server.app, "Plan 3 days in Tokyo", thread="o3")
    events = run(server.app, "[action]", forwarded={"action": "book_flight"}, thread="o3")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
    assert not openui_events(events)
