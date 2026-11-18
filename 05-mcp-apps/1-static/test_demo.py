from shared.testing import load_server, run

server = load_server(__file__)


def app_event(events):
    return next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "mcp_app")


def test_tool_result_comes_with_an_mcp_app_view():
    app = app_event(run(server.app, "Plan 3 days in Tokyo"))
    assert app["tool"]["_meta"]["ui"]["resourceUri"] == "ui://trip/card.html"
    assert app["resource"]["mimeType"] == "text/html;profile=mcp-app"
    assert "ui/initialize" in app["resource"]["html"]          # the view speaks the bridge itself
    assert app["result"]["structuredContent"]["title"] == "3 days in Tokyo"
    assert app["result"]["content"][0]["type"] == "text"        # what a non-MCP-Apps host would show
