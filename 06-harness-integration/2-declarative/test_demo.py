from shared.testing import load_server, run

server = load_server(__file__)
harness = server.harness

def test_agent_renders_a_valid_catalog_spec():
    from shared.catalog import validate_spec

    events = run(server.app, "Summarize my trip spending")
    ui = next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "render")
    assert ui["kind"] == "spec" and validate_spec(ui["spec"]) == []


def test_invalid_spec_comes_back_as_a_tool_result():
    output, ui = harness.run_tool("declarative", "render_ui", {"spec_json": '{"root": "a", "elements": {"a": {"type": "Carousel"}}}'})
    assert output.startswith("REJECTED") and "Carousel" in output and ui is None


def test_file_tools_cannot_leave_the_project_folder():
    import pytest

    for bad in ["../README.md", "/etc/passwd", "../../.env"]:
        with pytest.raises(ValueError):
            harness.run_tool("declarative", "read_file", {"path": bad})


def test_loop_stops_at_max_steps(monkeypatch):
    from shared import llm

    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"text": "", "tool_calls": [{"id": "x", "name": "list_files", "arguments": {}}]})
    events = run(server.app, "loop forever")
    assert sum(1 for e in events if e["type"] == "STEP_STARTED") == harness.MAX_STEPS
