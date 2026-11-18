from shared.testing import load_server, run

server = load_server(__file__)
harness = server.harness

def test_click_continues_the_same_conversation():
    run(server.app, "Summarize my trip spending", thread="h1")
    before = len(server.harness_app.SESSIONS["h1"]["messages"])
    events = run(server.app, "[action]", forwarded={"action": "show_unbooked"}, thread="h1")
    tools = [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"]
    assert tools == ["read_file", "render_ui"]
    ui = next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "render")
    assert "unbooked" in ui["spec"]["elements"]
    assert len(server.harness_app.SESSIONS["h1"]["messages"]) > before


def test_unknown_click_is_blocked():
    run(server.app, "Summarize my trip spending", thread="h2")
    events = run(server.app, "[action]", forwarded={"action": "book_everything"}, thread="h2")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
