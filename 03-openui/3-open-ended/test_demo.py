import json

from shared.testing import load_server, run

server = load_server(__file__)


def test_streamed_program_is_one_valid_htmlartifact():
    events = run(server.app, "Plan 3 days in Tokyo")
    program = "".join(e["value"]["delta"] for e in events if e["type"] == "CUSTOM" and e["name"] == "openui")
    result = server.openui.check(program, allow_html=True)
    assert result["errors"] == [] and result["components"].count("HtmlArtifact") == 1


def test_quotes_and_newlines_in_html_survive_escaping(monkeypatch):
    from shared import llm

    html = '<p class="x">it\'s "quoted"</p>\n<script>let s = "a\\nb";</script>'
    monkeypatch.setattr(llm, "stream", lambda *a, **k: iter([html[:10], html[10:]]))
    events = run(server.app, "x")
    program = "".join(e["value"]["delta"] for e in events if e["type"] == "CUSTOM" and e["name"] == "openui")
    start = program.index('HtmlArtifact("Trip widget", ') + len('HtmlArtifact("Trip widget", ')
    assert json.loads(program[start : program.rindex(")")]) == html
