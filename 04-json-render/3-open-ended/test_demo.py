from shared.testing import load_server, run

server = load_server(__file__)


def test_html_arrives_as_one_htmlframe_element():
    events = run(server.app, "Plan 3 days in Tokyo")
    lines = [e["value"]["line"] for e in events if e["type"] == "CUSTOM" and e["name"] == "jsonrender" and "line" in e["value"]]
    result = server.jr.check("\n".join(lines), allow_html=True)
    assert result["errors"] == [] and result["types"] == ["HtmlFrame"]


def test_htmlframe_is_not_in_the_plain_catalog():
    frame = '{"op":"add","path":"/root","value":"f"}\n{"op":"add","path":"/elements/f","value":{"type":"HtmlFrame","props":{"html":"<p/>","height":null,"actions":null},"children":[]}}'
    assert server.jr.check(frame)["errors"]
    assert server.jr.check(frame, allow_html=True)["errors"] == []
