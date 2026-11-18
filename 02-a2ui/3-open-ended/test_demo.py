from shared.testing import load_server, run

server = load_server(__file__)
a2ui = server.a2ui


def test_html_travels_as_a_custom_catalog_component():
    msgs = [e["value"] for e in run(server.app, "Plan 3 days in Tokyo") if e["type"] == "CUSTOM" and e["name"] == "a2ui"]
    assert msgs[0]["createSurface"]["catalogId"] == a2ui.TRIP_CATALOG_ID
    root = msgs[1]["updateComponents"]["components"][0]
    assert root["component"] == "HtmlFrame" and "<script>" in root["html"]


def test_basic_catalog_alone_rejects_htmlframe():
    update = a2ui.update_components("s", [{"id": "root", "component": "HtmlFrame", "html": "<p/>"}])
    assert a2ui.validate(update, allow_html=False)
    assert a2ui.validate(update, allow_html=True) == []
