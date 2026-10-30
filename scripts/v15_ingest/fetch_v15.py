"""V1.5 corpus expansion — fetch + cache raw_bytes from official sources.

Expansión de COBERTURA REAL sobre el método V1.4 (mismo fetcher, misma
política de provenance: raw_bytes preservados + SHA-256 por página +
timestamp UTC + HTTP status). NADA se inventa: solo se cachea lo que la
fuente devuelve.

Fuentes NUEVAS (secretariasenado.gov.co, http):
  - codigo_civil        (Código Civil — Ley 57 de 1887)        [CIVIL/FAMILIA]
  - ley_599_2000        (Código Penal — Ley 599 de 2000)      [PENAL]
  - ley_1437_2011       (CPACA — Ley 1437 de 2011)            [ADMINISTRATIVO]
  - decreto_410_1971    (Código de Comercio — Decreto 410/1971) [COMERCIAL]
  - ley_0100_1993       (Ley 100 de 1993 — texto consolidado) [SEGURIDAD SOCIAL]
  - ley_0080_1993       (Ley 80 de 1993 — texto consolidado)  [CONTRATACIÓN]

Fuentes NUEVAS (corteconstitucional.gov.co, https):
  - T-760-08, SU-360-99, C-355-06, C-239-97, C-075-07  [JURISPRUDENCIA]
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_SENADO = "http://www.secretariasenado.gov.co/senado/basedoc"
BASE_CORTE = "https://www.corteconstitucional.gov.co/relatoria"
V15_RAW = Path(__file__).parent / "v15_cache"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# (cache_key, slug-or-relatoria-id, kind, start_year_for_corte)
NORM_SOURCES = [
    ("codigo_civil", "codigo_civil"),
    ("ley_599_2000", "ley_0599_2000"),
    ("ley_1437_2011", "ley_1437_2011"),
    ("decreto_410_1971", "codigo_comercio"),
    ("ley_0100_1993", "ley_0100_1993"),
    ("ley_0080_1993", "ley_0080_1993"),
]
CORTE_SOURCES = [
    ("sentencia_T-760-2008", "2008/T-760-08.htm"),
    ("sentencia_SU-360-1999", "1999/SU-360-99.htm"),
    ("sentencia_C-355-2006", "2006/C-355-06.htm"),
    ("sentencia_C-239-1997", "1997/C-239-97.htm"),
    ("sentencia_C-075-2007", "2007/C-075-07.htm"),
]


def fetch_page(url: str, timeout: float = 30.0) -> dict:
    """Identical method to V1.4 fetch (fetch_sources.py): raw bytes + hash + timestamp."""
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return {
                "url": url,
                "http_status": r.status,
                "content_type": r.headers.get("Content-Type", ""),
                "raw_bytes": raw,
                "raw_bytes_hash": hashlib.sha256(raw).hexdigest(),
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "latency_ms": round((time.monotonic() - t0) * 1000, 2),
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "http_status": e.code, "error": str(e), "raw_bytes": b"", "raw_bytes_hash": ""}
    except urllib.error.URLError as e:
        return {"url": url, "http_status": 0, "error": str(e.reason), "raw_bytes": b"", "raw_bytes_hash": ""}


def next_page_link(html: str, current_url: str, slug: str = "") -> str | None:
    """Follow secretariasenado pagination — método EXACTO de V1.4:
    solo sigue enlaces del MISMO slug ({slug}_prNNN.html), nunca enlaces
    de normas relacionadas que la página también contiene."""
    import re

    pattern = re.compile(rf'href="({re.escape(slug)}_pr\d+\.html)"')
    links = sorted(set(pattern.findall(html)))
    for link in links:
        return link
    return None


def fetch_paginated(cache_key: str, slug: str) -> dict:
    """Fetch all pages of a paginated norma (method identical to V1.4)."""
    cache_dir = V15_RAW / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    if manifest_path.exists():
        return {"cache_key": cache_key, "cached": True}

    pages: list[dict] = []
    # First page: try .htm then .html (V1.4 used .htm for constitucion)
    first = fetch_page(f"{BASE_SENADO}/{slug}.htm")
    if first["http_status"] != 200:
        first = fetch_page(f"{BASE_SENADO}/{slug}.html")
    pages.append(first)
    if first["http_status"] != 200:
        err_manifest = [{k: v for k, v in p.items() if k != "raw_bytes"} for p in pages]
        (cache_dir / "manifest.json").write_text(
            json.dumps(err_manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return {"cache_key": cache_key, "pages": 0, "status": first["http_status"], "error": first.get("error")}

    idx = 0
    fetched: set[str] = set()
    pending: list[str] = []
    while True:
        try:
            html = pages[-1]["raw_bytes"].decode("latin-1")
        except UnicodeDecodeError:
            html = pages[-1]["raw_bytes"].decode("utf-8", errors="replace")
        # Método V1.4: encolar TODOS los enlaces del slug no visitados,
        # consumir en orden; sin refetch infinito.
        pattern = __import__("re").compile(rf'href="({__import__("re").escape(slug)}_pr\d+\.html)"')
        for link in sorted(set(pattern.findall(html))):
            if link not in fetched and link not in pending:
                pending.append(link)
        if not pending:
            break
        nxt = pending.pop(0)
        fetched.add(nxt)
        page = fetch_page(f"{BASE_SENADO}/{nxt}")
        pages.append(page)
        if page["http_status"] != 200:
            break
        idx += 1
        if idx > 120:  # hard cap de seguridad
            break
        time.sleep(0.5)  # polite delay

    # Save pages + manifest (mismo formato V1.4)
    manifest = []
    for i, p in enumerate(pages):
        fname = f"{slug}.htm" if i == 0 else f"{slug}_pr{i:03d}.html"
        (cache_dir / fname).write_bytes(p["raw_bytes"])
        manifest.append({
            "page_filename": fname,
            "page_index": i,
            "url": p["url"],
            "http_status": p["http_status"],
            "content_type": p.get("content_type", ""),
            "raw_bytes_size": len(p["raw_bytes"]),
            "raw_bytes_hash": p["raw_bytes_hash"],
            "retrieval_timestamp": p["retrieval_timestamp"],
            "latency_ms": p.get("latency_ms", 0),
            "cached_at": fname,
        })
    (cache_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    ok = sum(1 for p in pages if p["http_status"] == 200)
    return {"cache_key": cache_key, "pages": ok, "status": 200}


def fetch_sentencia(cache_key: str, rel_path: str) -> dict:
    """Fetch a single sentencia page from the Corte relatoria."""
    cache_dir = V15_RAW / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    if manifest_path.exists():
        return {"cache_key": cache_key, "cached": True}
    p = fetch_page(f"{BASE_CORTE}/{rel_path}")
    fname = "sentencia.htm"
    (cache_dir / fname).write_bytes(p["raw_bytes"])
    manifest = [{
        "sentencia_id": cache_key.replace("sentencia_", ""),
        "page_filename": fname,
        "url": p["url"],
        "http_status": p["http_status"],
        "content_type": p.get("content_type", ""),
        "raw_bytes_size": len(p["raw_bytes"]),
        "raw_bytes_hash": p["raw_bytes_hash"],
        "retrieval_timestamp": p["retrieval_timestamp"],
        "latency_ms": p.get("latency_ms", 0),
        "cached_at": fname,
    }]
    (cache_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return {"cache_key": cache_key, "pages": 1 if p["http_status"] == 200 else 0, "status": p["http_status"]}


def main() -> None:
    V15_RAW.mkdir(parents=True, exist_ok=True)
    print("=== V1.5 fetch — cobertura jurídica real ===")
    results = []
    for key, slug in NORM_SOURCES:
        r = fetch_paginated(key, slug)
        results.append(r)
        print(f"  {key}: {r}")
        time.sleep(0.6)
    for key, rel in CORTE_SOURCES:
        r = fetch_sentencia(key, rel)
        results.append(r)
        print(f"  {key}: {r}")
        time.sleep(0.6)
    failures = [r for r in results if r.get("status") not in (200, None) or r.get("pages", 0) == 0]
    print(f"\nTOTAL fuentes: {len(results)} | con fallo: {len(failures)}")
    if failures:
        print("FALLOS:", [f["cache_key"] for f in failures])


if __name__ == "__main__":
    main()
