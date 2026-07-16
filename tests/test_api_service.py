from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from scripts.api import app
from scripts.api_service import ValidationError, build_query_filter, calcular_estadisticas, load_dataset
from scripts.registro import registrar_prueba


def test_calcular_estadisticas_basicas():
    values = [10.0, 20.0, 30.0]
    stats = calcular_estadisticas(values)

    assert stats["suma"] == 60.0
    assert stats["conteo"] == 3
    assert stats["promedio"] == 20.0
    assert stats["minimo"] == 10.0
    assert stats["maximo"] == 30.0
    assert stats["mediana"] == 20.0
    assert stats["desviacion_estandar"] == pytest.approx(8.16496580927726, rel=1e-9)


def test_build_query_filter_rechaza_consultas_vacias():
    with pytest.raises(ValidationError, match="La lista de consultas no puede estar vacía"):
        build_query_filter([])


def test_load_dataset_from_sample_csv(tmp_path: Path):
    sample_csv = Path("data/transacciones_prueba.csv")
    output_path = tmp_path / "ventas_validas.parquet"

    df = load_dataset(sample_csv, output_path=output_path)

    assert not df.empty
    assert "MONTO APLICADO" in df.columns
    assert "GENERO_LABEL" in df.columns


def test_post_empty_payload_returns_validation_error():
    with TestClient(app) as client:
        response = client.post("/v1/estadisticas/ventas", json={})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == 400
    assert body["errorCode"] == "VF"
    assert body["errorLabel"] == "Validación Fallida"
    assert body["detail"] == "La lista de consultas no puede estar vacía"


def test_registrar_prueba_crea_archivo(tmp_path: Path):
    log_path = tmp_path / "pruebas.log"

    registrar_prueba("caso de ejemplo", 200, {"conteo": 3}, log_path=log_path)

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "caso de ejemplo" in content
    assert "200" in content


def test_build_query_filter_rechaza_fechas_invertidas():
    with pytest.raises(ValidationError, match="FECHA_DESDE"):
        build_query_filter(
            [
                {"consulta": "FECHA_DESDE", "valor": "2026-02-01T00:00:00"},
                {"consulta": "FECHA_HASTA", "valor": "2026-01-01T00:00:00"},
            ]
        )


def test_opciones_de_filtros_devuelven_valores_disponibles():
    with TestClient(app) as client:
        response = client.get("/v1/estadisticas/ventas/opciones")

    assert response.status_code == 200
    body = response.json()
    assert "GENERO" in body
    assert "CANAL" in body
    assert "LOCAL" in body


def test_post_invalid_filter_value_returns_validation_error():
    with TestClient(app) as client:
        response = client.post(
            "/v1/estadisticas/ventas",
            json={"consultas": [{"consulta": "LOCAL", "valor": "qwer"}]},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == 400
    assert body["errorCode"] == "VF"
    assert body["errorLabel"] == "Validación Fallida"
    assert "LOCAL" in body["detail"]
