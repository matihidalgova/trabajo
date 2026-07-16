"""Servicio de negocio para la API REST de estadísticas de ventas.

Contiene las funciones centrales que realizan:
- Carga y normalización del dataset (CSV -> Parquet).
- Validación y construcción de filtros admitidos por la API.
- Aplicación de filtros sobre el DataFrame y cálculo de métricas
    resumidas: suma, conteo, promedio, mínimo, máximo, mediana y
    desviación estándar.

También provee helpers de apoyo:
- ``obtener_opciones_filtros``: devuelve listas de valores repetitivos
    (p.ej. `GENERO`, `CANAL`, `LOCAL`) y el rango de fechas del dataset,
    usado por la API para exponer sugerencias al usuario.

Los errores de validación usan la excepción `ValidationError` y
son convertidos al formato de error esperado por los manejadores de
`scripts.api`.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.validacion import validar_rut, validar_uuid, validar_fecha

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "ventas_completas.csv"
DEFAULT_DATASET = ROOT / "data" / "ventas_api.parquet"
DEFAULT_LOG = ROOT / "logs.txt"

GENERO_LABELS = {
    "1": "Masculino",
    "2": "Femenino",
}

SUPPORTED_FILTERS = {
    "GENERO",
    "EDAD",
    "CANAL",
    "CODIGO_PRODUCTO",
    "ID_PERSONA",
    "LOCAL",
    "FECHA_DESDE",
    "FECHA_HASTA",
}


class ValidationError(ValueError):
    """Error de validación del cuerpo de la petición."""


class DatasetLoadError(RuntimeError):
    """Error al cargar o procesar el dataset."""


def _build_error_response(detail: str, status: int, method: str, instance: str = "/v1/estadisticas/ventas") -> dict[str, Any]:
    return {
        "detail": detail,
        "instance": instance,
        "status": status,
        "title": "Bad Request" if status == 400 else "Internal Server Error",
        "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400"
        if status == 400
        else "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errorCode": "VF" if status == 400 else "IE",
        "errorLabel": "Validación Fallida" if status == 400 else "Error Interno",
        "method": method,
    }


def validar_genero(valor: str) -> str:
    if valor in {"No especificado", "Masculino", "Femenino", "Otro"}:
        return valor
    raise ValidationError(f"El valor '{valor}' no es válido para GENERO")


def validar_edad(valor: str) -> int:
    try:
        edad = int(valor)
    except ValueError as exc:
        raise ValidationError(f"El valor '{valor}' no es un número entero válido para EDAD") from exc
    return edad


def validar_local(valor: str) -> int:
    try:
        local = int(valor)
    except ValueError as exc:
        raise ValidationError(f"El valor '{valor}' no es un número entero válido para LOCAL") from exc
    return local


def validar_fecha_iso(valor: str) -> str:
    try:
        datetime.fromisoformat(valor)
    except ValueError as exc:
        raise ValidationError(f"El valor '{valor}' no tiene formato ISO 8601 válido") from exc
    return valor


def build_query_filter(consultas: list[dict[str, Any]] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if consultas is None or len(consultas) == 0:
        raise ValidationError("La lista de consultas no puede estar vacía")

    filtros: dict[str, Any] = {}
    fecha_desde = None
    fecha_hasta = None
    for item in consultas:
        consulta = item.get("consulta")
        valor = item.get("valor")
        if consulta not in SUPPORTED_FILTERS:
            raise ValidationError(f"La consulta '{consulta}' no es válida")
        if consulta == "GENERO":
            filtros[consulta] = validar_genero(str(valor))
        elif consulta == "EDAD":
            filtros[consulta] = validar_edad(str(valor))
        elif consulta == "LOCAL":
            filtros[consulta] = validar_local(str(valor))
        elif consulta == "FECHA_DESDE":
            fecha_desde = validar_fecha_iso(str(valor))
            filtros[consulta] = fecha_desde
        elif consulta == "FECHA_HASTA":
            fecha_hasta = validar_fecha_iso(str(valor))
            filtros[consulta] = fecha_hasta
        else:
            filtros[consulta] = str(valor)

    if fecha_desde and fecha_hasta:
        if pd.Timestamp(fecha_desde) > pd.Timestamp(fecha_hasta):
            raise ValidationError("La FECHA_DESDE no puede ser posterior a la FECHA_HASTA")
    return filtros, consultas


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df["FECHA NACIMIENTO"] = pd.to_datetime(df["FECHA NACIMIENTO"], errors="coerce")
    df["MONTO APLICADO"] = pd.to_numeric(df["MONTO APLICADO"], errors="coerce")
    df["UNIDADES"] = pd.to_numeric(df["UNIDADES"], errors="coerce")
    df["LOCAL"] = pd.to_numeric(df["LOCAL"], errors="coerce")
    df["GENERO_LABEL"] = df["GENERO"].map(GENERO_LABELS).fillna("No especificado")
    edad = ((df["FECHA"] - df["FECHA NACIMIENTO"]).dt.days / 365.25)
    df["EDAD"] = pd.to_numeric(edad, errors="coerce").fillna(-1).astype(int)
    return df


def load_dataset(input_path: Path | str | None = None, output_path: Path | str | None = None) -> pd.DataFrame:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_DATASET)
    if not input_path.exists():
        raise DatasetLoadError(f"No existe el archivo de entrada: {input_path}")

    if output_path.exists():
        df = pd.read_parquet(output_path)
        if "GENERO_LABEL" not in df.columns:
            df = _normalize_dataframe(df)
            df.to_parquet(output_path, index=False)
        return df

    if input_path.suffix.lower() == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            rows = list(reader)
        if not rows:
            raise DatasetLoadError(f"El archivo CSV está vacío: {input_path}")
        header = [value.strip() for value in rows[0]]
        valid_rows = [row for row in rows[1:] if len(row) == len(header)]
        df = pd.DataFrame(valid_rows, columns=header)
        df = _normalize_dataframe(df)
        df.to_parquet(output_path, index=False)
        return df

    try:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "procesar_paralelo.py"),
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--workers",
                "2",
                "--executor",
                "thread",
            ],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DatasetLoadError(f"No se pudo generar el dataset de API: {exc.stderr or exc.stdout}") from exc

    if output_path.exists():
        return pd.read_parquet(output_path)

    df = pd.read_csv(input_path, sep=";", encoding="utf-8-sig")
    df = _normalize_dataframe(df)
    df.to_parquet(output_path, index=False)
    return df


def calcular_estadisticas(values: list[float] | pd.Series) -> dict[str, float | int]:
    if values is None:
        raise ValidationError("No hay valores para calcular estadísticas")

    series = values.dropna() if isinstance(values, pd.Series) else pd.Series(values).dropna()
    if series.empty:
        raise ValidationError("No hay valores para calcular estadísticas")

    suma = float(series.sum())
    conteo = int(series.count())
    promedio = float(series.mean())
    minimo = float(series.min())
    maximo = float(series.max())
    mediana = float(series.median())
    desviacion_estandar = float(series.std(ddof=0))
    return {
        "suma": suma,
        "conteo": conteo,
        "promedio": promedio,
        "minimo": minimo,
        "maximo": maximo,
        "mediana": mediana,
        "desviacion_estandar": desviacion_estandar,
    }


def apply_filters(df: pd.DataFrame, filtros: dict[str, Any]) -> pd.DataFrame:
    filtered = df.copy()
    if "GENERO" in filtros:
        filtered = filtered[filtered["GENERO_LABEL"] == filtros["GENERO"]]
    if "EDAD" in filtros:
        filtered = filtered[filtered["EDAD"] == filtros["EDAD"]]
    if "CANAL" in filtros:
        filtered = filtered[filtered["CANAL"] == filtros["CANAL"]]
    if "CODIGO_PRODUCTO" in filtros:
        filtered = filtered[filtered["SKU"].astype(str) == str(filtros["CODIGO_PRODUCTO"])]
    if "ID_PERSONA" in filtros:
        filtered = filtered[filtered["CODIGO CLIENTE"] == filtros["ID_PERSONA"]]
    if "LOCAL" in filtros:
        filtered = filtered[filtered["LOCAL"] == filtros["LOCAL"]]
    if "FECHA_DESDE" in filtros:
        filtered = filtered[filtered["FECHA"] >= pd.Timestamp(filtros["FECHA_DESDE"])]
    if "FECHA_HASTA" in filtros:
        filtered = filtered[filtered["FECHA"] <= pd.Timestamp(filtros["FECHA_HASTA"])]
    return filtered


def build_service_response(df: pd.DataFrame, method: str, filtros: dict[str, Any] | None = None) -> dict[str, Any]:
    filtered = apply_filters(df, filtros or {})
    values = filtered["MONTO APLICADO"].dropna()
    stats = calcular_estadisticas(values)
    return stats


def obtener_opciones_filtros(df: pd.DataFrame | None = None) -> dict[str, Any]:
    data = df if df is not None else load_dataset()
    return {
        "GENERO": ["No especificado", "Masculino", "Femenino", "Otro"],
        "CANAL": sorted([str(value) for value in data["CANAL"].dropna().astype(str).unique()]),
        "LOCAL": sorted([int(value) for value in data["LOCAL"].dropna().astype(int).unique()]),
        "FECHA_DESDE": data["FECHA"].min().strftime("%Y-%m-%dT%H:%M:%S") if not data["FECHA"].empty else None,
        "FECHA_HASTA": data["FECHA"].max().strftime("%Y-%m-%dT%H:%M:%S") if not data["FECHA"].empty else None,
    }


def bootstrap_dataset(input_path: Path | str | None = None, output_path: Path | str | None = None) -> pd.DataFrame:
    return load_dataset(input_path=input_path, output_path=output_path)
