"""Script de pruebas de la API REST para validar filtros y errores.

Ejecutar:
    python scripts/pruebas_api.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from scripts.registro import registrar_prueba

BASE_URL = "http://127.0.0.1:8000/v1/estadisticas/ventas"


def probar_caso(nombre: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> None:
    print(f"\n=== {nombre} ===")
    try:
        response = requests.post(BASE_URL, json=payload, params=params, timeout=30)
        registrar_prueba(nombre, response.status_code, response.json())
        print("status", response.status_code)
        print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:2000])
    except Exception as exc:  # pragma: no cover - script de diagnóstico
        print("error", exc)


if __name__ == "__main__":
    print("Esperando que la API esté disponible en", BASE_URL)
    for _ in range(20):
        try:
            requests.get(BASE_URL, params={"canal": "POS"}, timeout=3)
            break
        except requests.RequestException:
            time.sleep(1)
    else:
        print("La API no respondió. Iníciala primero con: python main.py")
        raise SystemExit(1)

    # Casos de éxito con combinaciones de filtros
    probar_caso("Sin filtros", payload={"consultas": []})
    probar_caso("Filtro simple GENERO", payload={"consultas": [{"consulta": "GENERO", "valor": "Femenino"}]})
    probar_caso("Filtro simple EDAD", payload={"consultas": [{"consulta": "EDAD", "valor": "31"}]})
    probar_caso("Filtro simple CANAL", payload={"consultas": [{"consulta": "CANAL", "valor": "POS"}]})
    probar_caso("Filtro simple CODIGO_PRODUCTO", payload={"consultas": [{"consulta": "CODIGO_PRODUCTO", "valor": "1001"}]})
    probar_caso("Filtro simple ID_PERSONA", payload={"consultas": [{"consulta": "ID_PERSONA", "valor": "00000000-0000-0000-0000-000000000000"}]})
    probar_caso("Filtro simple LOCAL", payload={"consultas": [{"consulta": "LOCAL", "valor": "209"}]})
    probar_caso("Filtro simple FECHA_DESDE", payload={"consultas": [{"consulta": "FECHA_DESDE", "valor": "2026-01-01T00:00:00"}]})
    probar_caso("Filtro simple FECHA_HASTA", payload={"consultas": [{"consulta": "FECHA_HASTA", "valor": "2026-06-30T23:59:59"}]})

    # Combinaciones múltiples de filtros
    probar_caso(
        "Combinación 1: GENERO + CANAL + LOCAL",
        payload={
            "consultas": [
                {"consulta": "GENERO", "valor": "Femenino"},
                {"consulta": "CANAL", "valor": "POS"},
                {"consulta": "LOCAL", "valor": "209"},
            ]
        },
    )
    probar_caso(
        "Combinación 2: EDAD + FECHA_DESDE + FECHA_HASTA",
        payload={
            "consultas": [
                {"consulta": "EDAD", "valor": "31"},
                {"consulta": "FECHA_DESDE", "valor": "2026-01-01T00:00:00"},
                {"consulta": "FECHA_HASTA", "valor": "2026-06-30T23:59:59"},
            ]
        },
    )
    probar_caso(
        "Combinación 3: CANAL + CODIGO_PRODUCTO + LOCAL",
        payload={
            "consultas": [
                {"consulta": "CANAL", "valor": "WEB"},
                {"consulta": "CODIGO_PRODUCTO", "valor": "1001"},
                {"consulta": "LOCAL", "valor": "209"},
            ]
        },
    )

    # Casos de error por filtro
    probar_caso("Error: consulta vacía", payload={})
    probar_caso("Error: consulta no soportada", payload={"consultas": [{"consulta": "RUT", "valor": "21.556.676-6"}]})
    probar_caso("Error: GENERO inválido", payload={"consultas": [{"consulta": "GENERO", "valor": "desconocido"}]})
    probar_caso("Error: EDAD inválida", payload={"consultas": [{"consulta": "EDAD", "valor": "abc"}]})
    probar_caso("Error: CANAL inválido", payload={"consultas": [{"consulta": "CANAL", "valor": "X"}]})
    probar_caso("Error: CODIGO_PRODUCTO inválido", payload={"consultas": [{"consulta": "CODIGO_PRODUCTO", "valor": ""}]})
    probar_caso("Error: ID_PERSONA con formato incorrecto", payload={"consultas": [{"consulta": "ID_PERSONA", "valor": "not-a-uuid"}]})
    probar_caso("Error: LOCAL inválido", payload={"consultas": [{"consulta": "LOCAL", "valor": "qwer"}]})
    probar_caso("Error: FECHA_DESDE inválida", payload={"consultas": [{"consulta": "FECHA_DESDE", "valor": "fecha-mala"}]})
    probar_caso("Error: FECHA_HASTA inválida", payload={"consultas": [{"consulta": "FECHA_HASTA", "valor": "2026/13/40"}]})

    # Casos de consultas con valores vacíos o nulos
    probar_caso("Error: valor vacío para GENERO", payload={"consultas": [{"consulta": "GENERO", "valor": ""}]})
    probar_caso("Error: valor nulo para LOCAL", payload={"consultas": [{"consulta": "LOCAL", "valor": None}]})
