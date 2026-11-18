from pathlib import Path

from shared.testing import load_server, run

server = load_server(__file__)


def test_html_arrives_in_a_custom_event():
    events = run(server.app, "Plan 3 days in Tokyo")
    html = next(e for e in events if e["type"] == "CUSTOM" and e["name"] == "html_ui")["value"]["html"]
    assert "<script>" in html and "Tokyo" in html


def test_code_fences_are_stripped(monkeypatch):
    monkeypatch.setattr(server.llm, "stream", lambda *a, **k: iter(["```html\n<p>hi</p>\n```"]))
    events = run(server.app, "x")
    html = next(e for e in events if e["type"] == "CUSTOM")["value"]["html"]
    assert html == "<p>hi</p>"


def test_sandbox_has_no_same_origin_and_blocks_network():
    js = (Path(__file__).parents[2] / "shared/web/sandbox.js").read_text()
    assert 'setAttribute("sandbox", "allow-scripts")' in js and "allow-same-origin" not in js.split("const CSP")[1]
    assert "default-src 'none'" in js
