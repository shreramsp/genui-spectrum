"""Helpers for the offline tests: load a demo's server.py and run one agent turn."""

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient


def load_server(test_file):
    """Import the server.py that sits next to `test_file`, under a unique module name."""
    path = Path(test_file).resolve().with_name("server.py")
    name = "server_" + "_".join(path.parent.parts[-2:]).replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(app, text, state=None, forwarded=None, thread="thread_test", path="/agent"):
    """POST one RunAgentInput and return the decoded AG-UI events as dicts."""
    body = {
        "threadId": thread,
        "runId": "run_test",
        "state": state or {},
        "messages": [{"id": "u1", "role": "user", "content": text}],
        "tools": [],
        "context": [],
        "forwardedProps": forwarded or {},
    }
    response = TestClient(app).post(path, json=body)
    assert response.status_code == 200, response.text
    return [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")]


def types(events):
    return [e["type"] for e in events]
