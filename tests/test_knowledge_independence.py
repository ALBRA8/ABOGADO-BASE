"""Independencia de ABOGADO-BASE respecto de DESPACHO-JURIDICO.

Después de la migración de conocimiento, el abogado NO debe depender
funcionalmente de la oficina para saber derecho:

    ABOGADO-BASE → conocimiento jurídico propio   ✓
    ABOGADO-BASE → DESPACHO-JURIDICO → conocimiento   ✗

Esta prueba escanea el código del abogado buscando dependencias hacia
el despacho (imports, paths, referencias funcionales) y falla si
encuentra alguna.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Patrones que indicarían dependencia funcional del despacho.
FORBIDDEN_PATTERNS = [
    # imports directos del paquete de la oficina
    (re.compile(r"^\s*(from|import)\s+despacho", re.MULTILINE), "import del paquete despacho"),
    (re.compile(r"^\s*from\s+src\.", re.MULTILINE), "import del harness de la oficina (src.*)"),
    (re.compile(r"^\s*(from|import)\s+matters\b", re.MULTILINE), "import de matters (oficina)"),
    (re.compile(r"^\s*(from|import)\s+marketplace\b", re.MULTILINE), "import de marketplace (oficina)"),
    (re.compile(r"^\s*(from|import)\s+whitelabel\b", re.MULTILINE), "import de whitelabel (oficina)"),
    # rutas del despacho en disco
    (re.compile(r"[\"'][^\"']*DESPACHO-JURIDICO[\"']"), "ruta al repositorio del despacho"),
    (re.compile(r"github\.com/ALBRA8/DESPACHO-JURIDICO"), "URL funcional al repo del despacho"),
]

# Directorios escaneados (todo el código del abogado).
SCAN_DIRS = ["albra", "scripts"]

# Exclusiones: menciones históricas/documentales legítimas (no código ejecutable).
ALLOWED_FILE_SUBSTRINGS = (
    # comentarios de origen/procedencia documentados
    "identity/agent.py",
    "__init__.py",
    "mcp/server.py",
    "llm/providers.py",
)


def _py_files() -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            out.extend(base.rglob("*.py"))
    return sorted(out)


def test_cero_dependencias_funcionales_del_despacho():
    """Cero imports/rutas funcionales hacia DESPACHO-JURIDICO."""
    violations: list[str] = []
    for path in _py_files():
        rel = str(path.relative_to(REPO_ROOT))
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, description in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                # Excluir comentarios que documentan origen (no ejecutables)
                line_start = text.rfind("\n", 0, match.start()) + 1
                line = text[line_start:text.find("\n", match.start()) if text.find("\n", match.start()) != -1 else len(text)]
                if line.strip().startswith("#"):
                    continue
                violations.append(f"{rel}: {description}: {line.strip()[:90]}")
    assert not violations, (
        "ABOGADO-BASE depende funcionalmente del despacho:\n" + "\n".join(violations)
    )


def test_corpus_vive_fisicamente_en_el_abogado():
    """El corpus jurídico está en disco dentro de ABOGADO-BASE (no referenciado)."""
    corpus_dir = REPO_ROOT / "albra" / "knowledge" / "colombia" / "corpus_pilot"
    assert corpus_dir.is_dir()
    v14_raw = corpus_dir / "v14_raw"
    assert v14_raw.is_dir()
    slugs = [d.name for d in v14_raw.iterdir() if d.is_dir()]
    assert "constitucion_1991" in slugs
    assert len(slugs) >= 6, f"esperados >=6 documentos raw, hay {len(slugs)}"
    # Manifests con provenance presentes
    manifests = list(v14_raw.rglob("manifest.json"))
    assert len(manifests) >= 6
