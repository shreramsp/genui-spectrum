import json

from shared.testing import load_server, run

server = load_server(__file__)
a2ui = server.a2ui


def test_offline_reply_passes_the_official_schema():
    assert server.check(json.loads(server.OFFLINE_REPLY)) == []


def test_run_sends_surface_components_then_data():
    events = run(server.app, "Plan 3 days in Tokyo")
    msgs = [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "a2ui"]
    assert [list(m)[1] for m in msgs] == ["createSurface", "updateComponents", "updateDataModel"]


def test_schema_errors_are_found():
    bad = {"components": [
        {"id": "root", "component": "Card", "children": ["a"]},   # Card takes ONE "child"
        {"id": "a", "component": "Text"},                          # Text needs "text"
        {"id": "b", "component": "Carousel"},                      # not in the catalog
        {"id": "c", "component": "Column", "children": ["nope"]},  # missing id
    ]}
    errors = " | ".join(server.check(bad))
    assert "child" in errors and "text" in errors and "Carousel" in errors and "nope" in errors


def test_htmlframe_is_not_allowed_in_declarative_mode():
    reply = {"components": [{"id": "root", "component": "HtmlFrame", "html": "<p>x</p>"}]}
    assert any("not allowed" in e for e in server.check(reply))


def test_action_echoes_bound_values():
    action = {"name": "save_checklist", "sourceComponentId": "save", "context": {"packing": {"suica": True}}}
    events = run(server.app, "[action]", forwarded={"a2uiAction": action})
    text = "".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "save_checklist" in text and "suica" in text
