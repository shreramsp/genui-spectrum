from shared.testing import load_server, run

server = load_server(__file__)
harness = server.harness

def test_agent_reads_files_then_renders_a_prebuilt_view():
    events = run(server.app, "Summarize my trip spending")
    tools = [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"]
    assert tools == ["list_files", "read_file", "show_budget"]
    ui = next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "render")
    assert ui["kind"] == "component" and sum(i["amount"] for i in ui["props"]["items"]) == 1433
    assert sum(1 for e in events if e["type"] == "STEP_STARTED") == 3
