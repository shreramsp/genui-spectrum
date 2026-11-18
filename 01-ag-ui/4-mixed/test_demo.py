from shared.catalog import actions_in
from shared.patch import apply_patch
from shared.testing import load_server, run

server = load_server(__file__)


def snapshot_of(events):
    return next(e for e in events if e["type"] == "STATE_SNAPSHOT")["snapshot"]


def test_first_turn_mixes_catalog_and_one_htmlframe():
    spec = snapshot_of(run(server.app, "Plan 3 days in Tokyo", thread="t_first"))["ui"]
    kinds = [el["type"] for el in spec["elements"].values()]
    assert kinds.count("HtmlFrame") == 1 and "Metric" in kinds
    assert actions_in(spec) == {"cheaper", "set_pace"}


def test_allowed_action_returns_a_small_delta():
    before = snapshot_of(run(server.app, "Plan 3 days in Tokyo", thread="t_action"))
    events = run(server.app, "[action] cheaper", forwarded={"action": "cheaper"}, thread="t_action")
    delta = next(e for e in events if e["type"] == "STATE_DELTA")["delta"]
    assert 0 < len(delta) < len(before["ui"]["elements"])  # only the changed parts travel
    after = apply_patch(before, delta)
    assert after["ui"]["elements"]["m_cost"]["props"]["value"] == "$455"


def test_unknown_action_is_blocked():
    run(server.app, "Plan 3 days in Tokyo", thread="t_block")
    events = run(server.app, "[action] book_flight", forwarded={"action": "book_flight"}, thread="t_block")
    assert any(e["type"] == "CUSTOM" and e["name"] == "action_blocked" for e in events)
    assert not any(e["type"].startswith("STATE_") for e in events)


def test_two_htmlframes_are_rejected():
    spec = {"root": "a", "elements": {
        "a": {"type": "Card", "props": {}, "children": ["x", "y"]},
        "x": {"type": "HtmlFrame", "props": {"html": "<p>1</p>"}},
        "y": {"type": "HtmlFrame", "props": {"html": "<p>2</p>"}},
    }}
    assert "use at most one HtmlFrame" in server.check(spec)
