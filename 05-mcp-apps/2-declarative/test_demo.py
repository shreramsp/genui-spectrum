from shared.testing import load_server, run

server = load_server(__file__)


def app_event(events):
    return next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "mcp_app")


def test_server_side_model_spec_is_valid_catalog_ui():
    from shared.catalog import validate_spec

    app = app_event(run(server.app, "Plan 3 days in Tokyo"))
    assert app["resource"]["uri"] == "ui://trip/genui.html"
    assert validate_spec(app["result"]["structuredContent"]["spec"]) == []
    assert "function renderSpec" in app["resource"]["html"]     # the renderer was pasted into the view
