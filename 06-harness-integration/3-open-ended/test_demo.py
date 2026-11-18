from shared.testing import load_server, run

server = load_server(__file__)
harness = server.harness

def test_agent_writes_html_from_the_file_data():
    events = run(server.app, "Summarize my trip spending")
    ui = next(e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == "render")
    assert ui["kind"] == "html" and "780" in ui["html"]
