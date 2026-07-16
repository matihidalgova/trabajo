"""Registro simple de eventos para pruebas y sesiones de uso de la API.

Genera archivos de texto en la carpeta data/ o en una ruta personalizada.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / "data" / "logs"
DEFAULT_TEST_LOG = DEFAULT_LOG_DIR / "pruebas_api.log"
DEFAULT_SESSION_LOG = DEFAULT_LOG_DIR / "sesion_api.log"


def _ensure_log_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def registrar_prueba(nombre: str, status: int, resultado: dict[str, Any] | None = None, log_path: Path | str | None = None) -> Path:
    log_path = Path(log_path or DEFAULT_TEST_LOG)
    _ensure_log_dir(log_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "timestamp": timestamp,
        "tipo": "prueba",
        "nombre": nombre,
        "status": status,
        "resultado": resultado or {},
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return log_path


def registrar_sesion_evento(metodo: str, path: str, status: int, detalle: dict[str, Any] | None = None, log_path: Path | str | None = None) -> Path:
    log_path = Path(log_path or DEFAULT_SESSION_LOG)
    _ensure_log_dir(log_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "timestamp": timestamp,
        "tipo": "sesion",
        "metodo": metodo,
        "path": path,
        "status": status,
        "detalle": detalle or {},
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return log_path
