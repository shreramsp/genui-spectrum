import json

from shared.testing import load_server, run

server = load_server(__file__)


def program_from(events):
    return "".join(e["value"].get("delta", "") for e in events if e["type"] == "CUSTOM" and e["name"] == "openui")


def test_template_filled_with_data_parses_cleanly():
    trip = json.loads(json.dumps(server.OFFLINE_REPLY))["tool_calls"][0]["arguments"]
    result = server.openui.check(server.fill(server.TEMPLATE, trip))
    assert result["errors"] == []
    assert {"Table", "BarChart", "Metric"} <= set(result["components"])


def test_run_streams_the_program_line_by_line():
    events = run(server.app, "Plan 3 days in Tokyo")
    deltas = [e for e in events if e["type"] == "CUSTOM" and e["name"] == "openui"]
    assert len(deltas) == len(server.TEMPLATE.strip().splitlines())
    assert program_from(events).startswith("root = Stack(")


def test_quotes_in_data_are_escaped():
    trip = {"title": 'The "best" trip', "days": [{"title": "A", "plan": "b"}], "budget": [{"category": "x", "amount": 1}], "tip": "t"}
    assert server.openui.check(server.fill(server.TEMPLATE, trip))["errors"] == []
