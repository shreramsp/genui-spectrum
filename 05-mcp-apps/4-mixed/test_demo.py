from shared.testing import load_server, run

server = load_server(__file__)


def app_event(events):
    return next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "mcp_app")

from fastapi.testclient import TestClient

client = TestClient(server.app)


def first_screen():
    return app_event(run(server.app, "Plan 3 days in Tokyo"))["result"]["structuredContent"]


def test_view_can_call_the_app_only_tool_through_the_host():
    screen = first_screen()
    reply = client.post("/tool", json={"name": "update_trip_screen", "arguments": {"screen_id": screen["screenId"], "action": "cheaper"}})
    assert reply.status_code == 200 and not reply.json().get("isError")
    assert reply.json()["structuredContent"]["spec"]["elements"]["m_cost"]["props"]["value"] == "$455"


def test_server_refuses_an_action_the_screen_never_offered():
    screen = first_screen()
    reply = client.post("/tool", json={"name": "update_trip_screen", "arguments": {"screen_id": screen["screenId"], "action": "book_flight"}})
    assert reply.json()["isError"] is True


def test_host_refuses_tools_the_server_does_not_have():
    assert client.post("/tool", json={"name": "delete_everything", "arguments": {}}).status_code == 403


def test_update_tool_is_hidden_from_the_model():
    import mcp_host

    tool = {"name": "update_trip_screen", "_meta": {"ui": {"visibility": ["app"]}}}
    assert "model" not in mcp_host.visibility(tool) and "app" in mcp_host.visibility(tool)
