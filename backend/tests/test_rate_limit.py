"""Rate limiter on the anonymous endpoints (gate try-it, live triage)."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.app.services import rate_limit
from src.app.services.rate_limit import SlidingWindowLimiter, enforce_orb_rate_limit
from src.settings import settings


def test_sliding_window_allows_up_to_limit_then_blocks():
    lim = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert lim.check("a", now=0.0)
    assert lim.check("a", now=1.0)
    assert lim.check("a", now=2.0)
    assert not lim.check("a", now=3.0)
    # A different key has its own budget.
    assert lim.check("b", now=3.0)
    # Once the oldest hit ages out of the window, capacity returns.
    assert lim.check("a", now=61.0)


def test_zero_limit_disables_gate():
    lim = SlidingWindowLimiter(limit=0, window_seconds=60)
    assert all(lim.check("a") for _ in range(50))


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping", dependencies=[Depends(enforce_orb_rate_limit)])
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    return app


def test_dependency_returns_429_per_ip(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rate_limit, "_per_ip", SlidingWindowLimiter(2, 300))
    monkeypatch.setattr(rate_limit, "_global", SlidingWindowLimiter(1000, 300))
    client = TestClient(_app())
    h1 = {"X-Forwarded-For": "8.8.8.8, 10.0.0.9, 127.0.0.1"}
    h2 = {"X-Forwarded-For": "9.9.9.9, 10.0.0.9, 127.0.0.1"}
    assert client.get("/ping", headers=h1).status_code == 200
    assert client.get("/ping", headers=h1).status_code == 200
    third = client.get("/ping", headers=h1)
    assert third.status_code == 429
    assert "Retry-After" in third.headers
    # Other public address is unaffected.
    assert client.get("/ping", headers=h2).status_code == 200


def test_spoofed_leading_xff_entries_do_not_reset_budget(monkeypatch: pytest.MonkeyPatch):
    """Clients control the LEFT of X-Forwarded-For; the ingress appends the
    real address on the right. Rightmost public IP must be the key."""
    monkeypatch.setattr(rate_limit, "_per_ip", SlidingWindowLimiter(1, 300))
    monkeypatch.setattr(rate_limit, "_global", SlidingWindowLimiter(1000, 300))
    client = TestClient(_app())
    assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1, 8.8.8.8, 127.0.0.1"}).status_code == 200
    assert client.get("/ping", headers={"X-Forwarded-For": "2.2.2.2, 8.8.8.8, 127.0.0.1"}).status_code == 429


def test_global_gate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rate_limit, "_per_ip", SlidingWindowLimiter(1000, 300))
    monkeypatch.setattr(rate_limit, "_global", SlidingWindowLimiter(1, 300))
    client = TestClient(_app())
    assert client.get("/ping", headers={"X-Forwarded-For": "8.8.8.8"}).status_code == 200
    assert client.get("/ping", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 429
