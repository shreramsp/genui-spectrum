"""The spending cap must refuse a call BEFORE anything is sent."""

import pytest

from shared import llm


@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "OFFLINE", False)
    monkeypatch.setattr(llm, "LEDGER", tmp_path / "spend.json")
    monkeypatch.setattr(llm, "_get_client", lambda: pytest.fail("a request was sent"))


def test_call_refused_when_cap_would_be_passed(live, monkeypatch):
    monkeypatch.setattr(llm, "SPEND_LIMIT_USD", 0.20)
    llm.LEDGER.write_text('{"spent_usd": 0.195}')
    with pytest.raises(llm.BudgetExceeded):
        llm.chat([{"role": "user", "content": "hi"}])
    with pytest.raises(llm.BudgetExceeded):
        list(llm.stream([{"role": "user", "content": "hi"}]))


def test_usage_is_recorded(live):
    llm._record(1_000_000, 0)
    assert llm.spent() == pytest.approx(llm.PRICE_IN)
