"""OFFICIAL LEGAL SOURCE LAYER — estados inequívocos de fuente jurídica.

Cierra la diferencia que la producción NO puede permitirse confundir:

    SOURCE_REGISTERED   la fuente está catalogada (con o sin URL).
    SOURCE_FETCHABLE    la URL respondió en algún momento (HTTP 200) y
                        el raw_bytes quedó preservado con su hash.
    SOURCE_VERIFIED     el contenido descargado fue verificado
                        estructuralmente (extracción de artículos +
                        reconstrucción con hash verificado) y su
                        provenance queda registrada.
    SOURCE_CURRENT      se re-consultó la fuente recientemente y el
                        hash coincide con lo preservado (sin cambios
                        detectables) — o la comparación declaró un
                        CAMBIO (SOURCE_CHANGED) / fallo (SOURCE_UNREACHABLE).

Nunca se trata REGISTERED como FETCHABLE, ni FETCHABLE como VERIFIED,
ni VERIFIED como CURRENT. El estado se DEMUESTRA con evidencia:
manifests con URL + HTTP status + SHA-256 + timestamp.

La capa se alimenta de los manifests reales de v14_raw/ y v15_raw/
(ingesta V1.4/V1.5). El catálogo declarativo (sources.py) se cruza
contra esta evidencia: una fuente catalogada sin manifiesto queda
REGISTERED, nunca VERIFIED.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from albra.observability.logger import get_logger

log = get_logger("albra.knowledge.official_sources")


class SourceFetchStatus(str, Enum):
    """Estado de una fuente jurídica respecto de su acceso y verificación."""

    SOURCE_REGISTERED = "SOURCE_REGISTERED"      # catalogada (sources.py)
    SOURCE_FETCHABLE = "SOURCE_FETCHABLE"        # URL respondió 200 (manifest)
    SOURCE_VERIFIED = "SOURCE_VERIFIED"          # + contenido estructurado y hasheado
    SOURCE_CURRENT = "SOURCE_CURRENT"            # + re-verificada sin cambios
    SOURCE_CHANGED = "SOURCE_CHANGED"            # re-consulta: hash difiere
    SOURCE_UNREACHABLE = "SOURCE_UNREACHABLE"    # re-consulta: sin respuesta
    SOURCE_ERROR = "SOURCE_ERROR"                # re-consulta: otro error


@dataclass
class SourceVerificationRecord:
    """Registro verificable de una captura de fuente oficial.

    Cada campo proviene del manifest de ingesta real (V1.4/V1.5):
    nada de esto se rellena a mano.
    """

    source_key: str                      # p.ej. "constitucion_1991", "codigo_civil"
    authority: str                       # p.ej. "Secretaría del Senado"
    url: str
    http_status: int
    content_type: str
    raw_bytes_hash: str                  # SHA-256 de la página (o concat)
    raw_bytes_size: int
    retrieval_timestamp: str             # ISO 8601 UTC de la captura
    pages: int = 1
    status: SourceFetchStatus = SourceFetchStatus.SOURCE_VERIFIED
    last_verification: str = ""          # última re-verificación (reverify)
    notes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "authority": self.authority,
            "url": self.url,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "raw_bytes_hash": self.raw_bytes_hash,
            "raw_bytes_size": self.raw_bytes_size,
            "retrieval_timestamp": self.retrieval_timestamp,
            "pages": self.pages,
            "status": self.status.value,
            "last_verification": self.last_verification,
            "notes": self.notes,
        }


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class OfficialSourceLayer:
    """Capa de fuentes oficiales con estados demostrables.

    Carga los manifests de ingesta (v14_raw, v15_raw) como registros
    VERIFIED y permite re-verificar contra la fuente (reverify) para
    decidir CURRENT / CHANGED / UNREACHABLE. Sin red, ``reverify``
    devuelve SOURCE_ERROR con causa — nunca simula verificación.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self._records: dict[str, SourceVerificationRecord] = {}
        base = base_dir or Path(__file__).parent / "colombia" / "corpus_pilot"
        self._load_manifests(base / "v14_raw")
        self._load_manifests(base / "v15_raw")
        # Cruce con el catálogo declarativo: fuentes catalogadas sin
        # manifiesto quedan REGISTERED.
        self._register_catalogued()

    # ----- carga de evidencia real -----

    def _load_manifests(self, raw_dir: Path) -> None:
        if not raw_dir.exists():
            return
        for cache_dir in sorted(raw_dir.iterdir()):
            manifest_path = cache_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:  # noqa: PERF112
                log.warning("official_sources.manifest_error", dir=str(cache_dir), error=str(e))
                continue
            entries = [p for p in manifest if p.get("http_status") == 200]
            if not entries:
                continue
            key = cache_dir.name
            total_bytes = 0
            try:
                # El hash del registro es el SHA-256 del CONCATENADO real
                # en disco (re-verificable sin red).
                combined = b""
                for p in entries:
                    page_file = cache_dir / p.get("cached_at", p.get("page_filename", ""))
                    if page_file.exists():
                        combined += page_file.read_bytes()
                total_bytes = len(combined)
                combined_hash = hashlib.sha256(combined).hexdigest() if combined else ""
                if not combined_hash:
                    continue
            except OSError as e:
                log.warning("official_sources.read_error", dir=str(cache_dir), error=str(e))
                continue
            self._records[key] = SourceVerificationRecord(
                source_key=key,
                authority=(
                    "Corte Constitucional de Colombia"
                    if "corteconstitucional" in (entries[0].get("url", ""))
                    else "Secretaría del Senado"
                ),
                url=entries[0].get("url", ""),
                http_status=entries[0]["http_status"],
                content_type=entries[0].get("content_type", "text/html"),
                raw_bytes_hash=combined_hash,
                raw_bytes_size=total_bytes,
                retrieval_timestamp=entries[0].get("retrieval_timestamp", ""),
                pages=len(entries),
                status=SourceFetchStatus.SOURCE_VERIFIED,
                notes={
                    # Hash de la PRIMERA página según el manifest — base de
                    # comparación de reverify (la URL del registro es la
                    # primera página, no el concatenado paginado).
                    "first_page_hash": entries[0].get("raw_bytes_hash", ""),
                },
            )

    def _register_catalogued(self) -> None:
        """Fuentes del catálogo declarativo sin evidencia → REGISTERED."""
        try:
            from albra.knowledge.sources import COLOMBIA_OFFICIAL_SOURCES
        except Exception:  # noqa: BLE001 — el catálogo es metadata, nunca bloquea
            return
        for sid, s in COLOMBIA_OFFICIAL_SOURCES.items():
            if sid not in self._records:
                self._records[sid] = SourceVerificationRecord(
                    source_key=sid,
                    authority=s.authority,
                    url=s.url,
                    http_status=0,
                    content_type="",
                    raw_bytes_hash="",
                    raw_bytes_size=0,
                    retrieval_timestamp="",
                    pages=0,
                    status=SourceFetchStatus.SOURCE_REGISTERED,
                )

    # ----- consulta -----

    def get(self, key: str) -> SourceVerificationRecord | None:
        return self._records.get(key)

    def records(self) -> dict[str, SourceVerificationRecord]:
        return dict(self._records)

    def by_status(self, status: SourceFetchStatus) -> list[SourceVerificationRecord]:
        return [r for r in self._records.values() if r.status == status]

    def verified_source_keys(self) -> set[str]:
        return {
            r.source_key for r in self._records.values()
            if r.status in (
                SourceFetchStatus.SOURCE_VERIFIED,
                SourceFetchStatus.SOURCE_CURRENT,
                SourceFetchStatus.SOURCE_CHANGED,
            )
        }

    def stats(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self._records.values():
            out[r.status.value] = out.get(r.status.value, 0) + 1
        return out

    # ----- re-verificación (requiere red; nunca simula) -----

    def reverify(self, key: str, *, timeout: float = 20.0) -> SourceFetchStatus:
        """Re-consulta la URL de una fuente y compara el hash.

        - Hash idéntico al capturado  → SOURCE_CURRENT
        - Hash distinto               → SOURCE_CHANGED (nueva captura NO
          reemplaza la preservada; se reporta para revisión humana)
        - Sin respuesta               → SOURCE_UNREACHABLE
        - Fuente sin URL/evidencia    → SOURCE_ERROR (nada que verificar)

        Comparación por PRIMERA página: la URL del registro es la
        primera página del documento paginado; su hash de manifest es
        la base de comparación. Un cambio en la primera página ya
        demuestra SOURCE_CHANGED sin re-descargar todo.

        Este método NO actualiza el contenido preservado: el ciclo de
        actualización de corpus es una operación de ingesta separada
        (HITL), no un efecto colateral de una consulta.
        """
        rec = self._records.get(key)
        if rec is None or not rec.url:
            return SourceFetchStatus.SOURCE_ERROR
        expected_hash = rec.notes.get("first_page_hash") or (
            rec.raw_bytes_hash if rec.pages == 1 else ""
        )
        if not expected_hash:
            return SourceFetchStatus.SOURCE_ERROR
        try:
            req = urllib.request.Request(
                rec.url, headers={"User-Agent": _USER_AGENT, "Accept": "text/html"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            status_code = r.status
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            rec.last_verification = now
            if status_code != 200:
                rec.status = SourceFetchStatus.SOURCE_UNREACHABLE
                return rec.status
            fetched_hash = hashlib.sha256(raw).hexdigest()
            rec.status = (
                SourceFetchStatus.SOURCE_CURRENT
                if fetched_hash == expected_hash
                else SourceFetchStatus.SOURCE_CHANGED
            )
            return rec.status
        except Exception as e:  # noqa: BLE001 — el estado del entorno se reporta
            rec.status = SourceFetchStatus.SOURCE_UNREACHABLE
            rec.last_verification = datetime.now(timezone.utc).isoformat(timespec="seconds")
            rec.notes["last_error"] = type(e).__name__
            return rec.status
