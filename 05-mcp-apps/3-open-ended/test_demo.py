from shared.testing import load_server, run

server = load_server(__file__)


def app_event(events):
    return next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "mcp_app")


def test_html_travels_as_structured_content_for_a_nested_sandbox():
    app = app_event(run(server.app, "Plan 3 days in Tokyo"))
    assert "<script>" in app["result"]["structuredContent"]["html"]
    assert "function mountSandbox" in app["resource"]["html"]
