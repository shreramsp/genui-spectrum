import json

from shared.testing import load_server, run

server = load_server(__file__)
a2ui = server.a2ui


def a2ui_messages(events):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "a2ui"]


def test_fixed_surface_is_valid_a2ui():
    message = a2ui.update_components("trip", server.COMPONENTS)
    assert a2ui.validate(message) == []
    assert a2ui.tree_errors(server.COMPONENTS) == []


def test_structure_arrives_before_data_and_all_messages_validate():
    msgs = a2ui_messages(run(server.app, "Plan 3 days in Tokyo", thread="s1"))
    kinds = [next(k for k in m if k != "version") for m in msgs]
    assert kinds == ["createSurface", "updateComponents", "updateDataModel", "updateDataModel"]
    assert all(a2ui.validate(m) == [] for m in msgs)


def test_replan_action_changes_only_the_data():
    run(server.app, "Plan 3 days in Tokyo", thread="s2")
    action = {"name": "replan", "surfaceId": "trip", "sourceComponentId": "replan", "timestamp": "t", "context": {"days": 5, "style": ["budget"]}}
    msgs = a2ui_messages(run(server.app, "[action] replan", forwarded={"a2uiAction": action}, thread="s2"))
    assert [list(m)[1] for m in msgs] == ["updateDataModel"]
    assert len(msgs[0]["updateDataModel"]["value"]["days"]) == 5


def test_data_with_wrong_shape_is_rejected():
    check = server.check_data(3)
    assert check({"title": "x"})  # missing fields
    good = json.loads(server.OFFLINE_FIRST)
    assert check(good) == []


def test_unknown_action_is_blocked():
    events = run(server.app, "x", forwarded={"a2uiAction": {"name": "book_hotel", "context": {}}}, thread="s3")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
