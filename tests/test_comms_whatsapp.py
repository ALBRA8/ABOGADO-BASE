"""Tests de conexión del adapter WhatsApp Cloud API.

Cubre los fallos reales detectados comparando con el daemon estable
del CRM (guía, no copia — protocolos distintos):
    * webhook multi-entry/multi-change (antes solo entry[0]/changes[0])
    * crash de metadata_extra (campo inexistente en ChannelMessage)
    * reintentos transitorios con backoff + Retry-After en 429
    * errores no transitorios (401/400) fallan de inmediato
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from albra.comms.adapters.whatsapp import WhatsAppAdapter
from albra.config.settings import Settings


def _adapter() -> WhatsAppAdapter:
    s = Settings()
    s.whatsapp_token = "test-token"
    s.whatsapp_phone_id = "1234567890"
    return WhatsAppAdapter(s)


def _multi_entry_webhook() -> dict:
    """Webhook con 2 entries y 2 changes — Meta puede agrupar así."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "573001111111", "profile": {"name": "Ana"}}],
                            "messages": [{"id": "wamid.A", "type": "text", "text": {"body": "hola"}}],
                        }
                    },
                    {
                        "value": {
                            "contacts": [{"wa_id": "573001111111", "profile": {"name": "Ana"}}],
                            "messages": [{"id": "wamid.B", "type": "text", "text": {"body": "segundo"}}],
                        }
                    },
                ]
            },
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "573002222222"}],
                            "messages": [{"id": "wamid.C", "type": "text", "text": {"body": "otro chat"}}],
                        }
                    }
                ]
            },
        ]
    }


# ----------------------------------------------------------------------
# webhook_push
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_multi_entry_multi_change() -> None:
    """Todos los mensajes de TODAS las entries/changes se reciben."""
    ad = _adapter()
    ad.webhook_push(_multi_entry_webhook())
    msgs = await ad.receive()
    assert [m.text for m in msgs] == ["hola", "segundo", "otro chat"]
    assert {m.user for m in msgs} == {"573001111111", "573002222222"}


@pytest.mark.asyncio
async def test_webhook_contact_name_no_crash() -> None:
    """El nombre del contacto no rompe el parseo (bug metadata_extra)."""
    ad = _adapter()
    ad.webhook_push(_multi_entry_webhook())
    msgs = await ad.receive()
    assert msgs[0].raw.get("_contact_name") == "Ana"


@pytest.mark.asyncio
async def test_webhook_status_only_is_ignored() -> None:
    """Webhook solo de estados (delivery receipts) no genera mensajes."""
    ad = _adapter()
    ad.webhook_push(
        {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.X", "status": "delivered"}]}}]}]}
    )
    assert await ad.receive() == []


@pytest.mark.asyncio
async def test_webhook_malformed_does_not_raise() -> None:
    """Payload corrupto: se registra last_error, no explota."""
    ad = _adapter()
    ad.webhook_push({"entry": "no-soy-una-lista"})
    assert await ad.receive() == []
    assert ad.last_error is not None and "webhook.parse_fail" in ad.last_error


# ----------------------------------------------------------------------
# send(): reintentos y clasificación de errores
# ----------------------------------------------------------------------


class _Resp:
    def __init__(self, status: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = str(self._payload)

    def json(self) -> dict:
        return self._payload

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class _FlakyClient:
    """AsyncClient de mentira: falla N veces y luego responde 200."""

    def __init__(self, failures: list[_Resp | Exception]):
        self._failures = list(failures)
        self.calls = 0

    async def post(self, *a, **kw):
        self.calls += 1
        item = self._failures.pop(0) if self._failures else _Resp(200, {"messages": [{"id": "ok"}]})
        if isinstance(item, Exception):
            raise item
        return item

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_send_retries_transient_then_succeeds(monkeypatch) -> None:
    """Timeout en el 1er intento → reintento → 200. Nunca 'ok: False'."""
    ad = _adapter()
    client = _FlakyClient([httpx.TimeoutException("boom")])
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    out = await ad.send("573001111111", "hola")
    assert out["ok"] is True
    assert client.calls == 2
    assert ad.last_error is None


@pytest.mark.asyncio
async def test_send_429_honors_retry_after(monkeypatch) -> None:
    """429 con Retry-After=1 → espera y reintenta → éxito."""
    ad = _adapter()
    client = _FlakyClient([_Resp(429, {"error": {"message": "rate"}}, {"retry-after": "1"})])
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
    slept: list[float] = []
    monkeypatch.setattr(asyncio, "sleep", lambda d: _record_sleep(d, slept))
    out = await ad.send("573001111111", "hola")
    assert out["ok"] is True
    assert client.calls == 2
    assert slept and slept[0] <= ad.MAX_RETRY_AFTER


@pytest.mark.asyncio
async def test_send_401_fails_immediately(monkeypatch) -> None:
    """401 (token inválido): SIN reintentos — falla en el 1er intento."""
    ad = _adapter()
    client = _FlakyClient([_Resp(401, {"error": {"message": "bad token"}})])
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
    out = await ad.send("573001111111", "hola")
    assert out["ok"] is False
    assert client.calls == 1
    assert "401" in (out.get("error") or "")
    assert ad.last_error and "401" in ad.last_error


@pytest.mark.asyncio
async def test_send_exhausts_retries_returns_last_error(monkeypatch) -> None:
    """Red caída los 3 intentos → ok False con last_error visible."""
    ad = _adapter()
    client = _FlakyClient([httpx.TimeoutException("x")] * 5)
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    out = await ad.send("573001111111", "hola")
    assert out["ok"] is False
    assert client.calls == ad.MAX_SEND_ATTEMPTS
    assert "transient" in (out.get("error") or "")


@pytest.mark.asyncio
async def test_send_without_config_fails_explicitly() -> None:
    """Sin token/phone_id: error explícito (no simula éxito)."""
    s = Settings()
    s.whatsapp_token = ""
    s.whatsapp_phone_id = ""
    ad = WhatsAppAdapter(s)
    out = await ad.send("573001111111", "hola")
    assert out["ok"] is False
    assert "WHATSAPP_TOKEN" in (out.get("error") or "")


# ----------------------------------------------------------------------


async def _no_sleep(_delay: float) -> None:  # pragma: no cover
    return None


async def _record_sleep(delay: float, bucket: list[float]) -> None:
    bucket.append(delay)
