"""
WhatsApp Cloud API Adapter (Meta).

NO simula la integración. Si no hay token configurado, falla explícitamente.
Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api

Fiabilidad de conexión (lecciones del daemon estable del CRM, adaptadas al
protocolo HTTP sin estado de la Cloud API):
    * Los webhooks de Meta pueden traer VARIAS entries y VARIAS changes
      en un solo POST — se procesan todas (antes solo entry[0]/changes[0]).
    * El envío reintenta fallos TRANSITORIOS (red, timeout, 5xx) con
      backoff corto y honra ``Retry-After`` en 429. Los errores de
      configuración (400/401/403) fallan de inmediato: reintentar no ayuda.
    * El último error queda visible en ``last_error`` para diagnóstico
      (doctor / logs) en vez de perderse.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from albra.comms.base import ChannelAdapter, ChannelMessage
from albra.config.settings import Settings
from albra.observability.logger import get_logger

# Errores HTTP que NO valen la pena reintentar (configuración/permisos).
_NON_TRANSIENT_HTTP = {400, 401, 403, 404}


class WhatsAppAdapter(ChannelAdapter):
    name = "whatsapp"

    BASE_URL = "https://graph.facebook.com/v18.0"

    # Reintentos de envío ante fallos transitorios (backoff corto:
    # 0.5s, 1.0s, 2.0s — total ~3.5s para no bloquear la respuesta).
    MAX_SEND_ATTEMPTS = 3
    RETRY_BACKOFF = (0.5, 1.0, 2.0)
    # Techo para el Retry-After de 429 (evita colgarse minutos).
    MAX_RETRY_AFTER = 5.0

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.log = get_logger("albra.comms.whatsapp")
        self._token = settings.whatsapp_token
        self._phone_id = settings.whatsapp_phone_id
        self._incoming: list[ChannelMessage] = []
        self.last_error: str | None = None  # visible para doctor/logs

    # ------------------------------------------------------------------
    # Recepción (webhook push)
    # ------------------------------------------------------------------

    async def receive(self) -> list[ChannelMessage]:
        # WhatsApp envía webhooks - necesitamos un endpoint HTTP.
        # Aquí solo devolvemos lo que llegó vía webhook_push().
        msgs = list(self._incoming)
        self._incoming.clear()
        return msgs

    def webhook_push(self, payload: dict[str, Any]) -> None:
        """Procesa un webhook de WhatsApp Cloud API.

        Meta puede agrupar varias ``entry`` y varias ``changes`` en un
        mismo POST: se iteran todas (no solo la primera).
        """
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [{}])
                    contact = contacts[0] if contacts else {}
                    user = contact.get("wa_id", "unknown")
                    name = contact.get("profile", {}).get("name", "")
                    for m in messages:
                        text = m.get("text", {}).get("body", "")
                        raw = dict(m)
                        if name:
                            raw["_contact_name"] = name
                        self._incoming.append(
                            ChannelMessage(
                                channel="whatsapp",
                                user=user,
                                text=text,
                                ts=time.time(),
                                raw=raw,
                            )
                        )
        except (AttributeError, KeyError, IndexError, TypeError) as e:
            self.last_error = f"webhook.parse_fail: {e!r}"
            self.log.warning("whatsapp.webhook.parse_fail", error=str(e))

    # ------------------------------------------------------------------
    # Envío (Graph API) con reintentos transitorios
    # ------------------------------------------------------------------

    async def send(self, to: str, text: str, *, reply_to: str | None = None) -> dict[str, Any]:
        if not self._token or not self._phone_id:
            self.last_error = "WHATSAPP_TOKEN o PHONE_ID no configurados"
            return {"ok": False, "error": self.last_error}
        try:
            import httpx  # type: ignore[import]
        except ImportError:
            self.last_error = "httpx no instalado"
            return {"ok": False, "error": self.last_error}

        url = f"{self.BASE_URL}/{self._phone_id}/messages"
        headers = {"Authorization": f"Bearer {self._token}"}
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        if reply_to:
            body["context"] = {"message_id": reply_to}

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            for attempt in range(1, self.MAX_SEND_ATTEMPTS + 1):
                try:
                    r = await client.post(url, headers=headers, json=body)
                    if r.status_code in _NON_TRANSIENT_HTTP:
                        # Configuración/permisos: reintentar no ayuda.
                        self.last_error = (
                            f"HTTP {r.status_code} (no transitorio): {r.text[:200]}"
                        )
                        self.log.error("whatsapp.send.non_transient", status=r.status_code)
                        return {"ok": False, "error": self.last_error}
                    if r.status_code == 429:
                        retry_after = self._retry_after_seconds(r)
                        self.log.warning(
                            "whatsapp.send.rate_limited",
                            attempt=attempt,
                            retry_after=retry_after,
                        )
                    elif r.is_success:
                        self.last_error = None
                        return {"ok": True, "response": r.json()}
                    else:  # 5xx u otro código transitorio
                        self.log.warning(
                            "whatsapp.send.transient_http",
                            status=r.status_code,
                            attempt=attempt,
                        )
                except (httpx.TimeoutException, httpx.TransportError) as e:
                    # Red/timeout: fallo transitorio → backoff y reintento.
                    self.last_error = f"transient: {e!r}"
                    self.log.warning(
                        "whatsapp.send.transient_network", attempt=attempt, error=str(e)
                    )
                    retry_after = self.RETRY_BACKOFF[min(attempt - 1, len(self.RETRY_BACKOFF) - 1)]

                if attempt < self.MAX_SEND_ATTEMPTS:
                    await asyncio.sleep(retry_after)

        self.log.error("whatsapp.send.error", error=str(self.last_error))
        return {"ok": False, "error": self.last_error or "envío fallido tras reintentos"}

    @staticmethod
    def _retry_after_seconds(response: Any) -> float:
        """Extrae Retry-After del 429 (techo MAX_RETRY_AFTER)."""
        try:
            raw = response.headers.get("retry-after")
            return min(float(raw), WhatsAppAdapter.MAX_RETRY_AFTER) if raw else 1.0
        except (TypeError, ValueError):
            return 1.0

    async def startup(self) -> None:
        if not self._token:
            self.log.warning("whatsapp.startup.no_token")
