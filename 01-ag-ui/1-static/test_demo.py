import json

from shared.testing import load_server, run, types

server = load_server(__file__)


def test_run_is_wrapped_in_started_and_finished():
    t = types(run(server.app, "Plan 3 days in Tokyo"))
    assert t[0] == "RUN_STARTED" and t[-1] == "RUN_FINISHED"


def test_tool_calls_stream_as_start_args_end():
    events = run(server.app, "Plan 3 days in Tokyo")
    starts = [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert [s["toolCallName"] for s in starts] == ["show_itinerary", "show_budget"]

    # Re-assemble the streamed ARGS exactly like app.js does.
    call_id = starts[0]["toolCallId"]
    args = "".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS" and e["toolCallId"] == call_id)
    assert json.loads(args)["city"] == "Tokyo"


def test_unknown_tool_is_not_forwarded(monkeypatch):
    fake = {"text": "hi", "tool_calls": [{"id": "x", "name": "delete_everything", "arguments": {}}]}
    monkeypatch.setattr(server.llm, "chat", lambda *a, **k: fake)
    events = run(server.app, "anything")
    assert not any(e["type"] == "TOOL_CALL_START" for e in events)
