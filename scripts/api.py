"""API REST para consultar estadísticas resumidas de ventas.

Este módulo expone los endpoints GET y POST de la ruta base
/v1/estadisticas/ventas y delega la lógica de negocio al servicio
contenida en :mod:`scripts.api_service`.

Características importantes:
- Endpoints `GET` y `POST` para consultas resumidas y parametrizadas.
- Manejadores de excepción que devuelven el formato de error exigido
    por el enunciado (códigos 400/500 con `errorCode`).
- Soporte para carga inicial del dataset (bootstrapping) en el evento
    de startup.
- Generación personalizada de OpenAPI: las opciones disponibles para
    filtros (`/v1/estadisticas/ventas/opciones`) se inyectan en las
    descripciones de los parámetros del esquema OpenAPI para facilitar
    sugerencias en la UI sin forzar `enum` (manteniendo inputs de texto
    libre en Swagger UI).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from scripts.api_service import (
    ValidationError,
    _build_error_response,
    bootstrap_dataset,
    build_query_filter,
    build_service_response,
    obtener_opciones_filtros,
)
from scripts.registro import registrar_sesion_evento
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Cruz Morada - Estadísticas de ventas",
    version="1.0.0",
    description="API REST para consultar estadísticas resumidas de ventas con filtros opcionales. En la implementación actual, los datos se leen desde archivos CSV/Parquet en disco; no se usa una base de datos relacional.",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_build_error_response(str(exc), 400, request.method),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_build_error_response(str(exc), 400, request.method),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_build_error_response(str(exc), 500, request.method),
    )


@app.on_event("startup")
def startup_event() -> None:
    bootstrap_dataset()


@app.get(
    "/v1/estadisticas/ventas",
    tags=["Estadísticas"],
    summary="Consultar estadísticas con filtros opcionales",
    description="Calcula las estadísticas a partir del dataset cargado desde archivos CSV/Parquet en disco. No se requiere una base de datos para esta implementación.",
    responses={
        200: {"description": "Estadísticas calculadas correctamente."},
        400: {"description": "Error de validación de filtros."},
        500: {"description": "Error interno del servidor."},
    },
)
def get_estadisticas(request: Request, genero: str | None = None, edad: int | None = None, canal: str | None = None, codigo_producto: str | None = None, id_persona: str | None = None, local: int | None = None, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict[str, Any]:
    consultas: list[dict[str, Any]] = []
    if genero is not None:
        consultas.append({"consulta": "GENERO", "valor": genero})
    if edad is not None:
        consultas.append({"consulta": "EDAD", "valor": str(edad)})
    if canal is not None:
        consultas.append({"consulta": "CANAL", "valor": canal})
    if codigo_producto is not None:
        consultas.append({"consulta": "CODIGO_PRODUCTO", "valor": codigo_producto})
    if id_persona is not None:
        consultas.append({"consulta": "ID_PERSONA", "valor": id_persona})
    if local is not None:
        consultas.append({"consulta": "LOCAL", "valor": str(local)})
    if fecha_desde is not None:
        consultas.append({"consulta": "FECHA_DESDE", "valor": fecha_desde})
    if fecha_hasta is not None:
        consultas.append({"consulta": "FECHA_HASTA", "valor": fecha_hasta})

    filtros, _ = build_query_filter(consultas) if consultas else ({}, [])
    df = bootstrap_dataset()
    response = build_service_response(df, request.method, filtros)
    registrar_sesion_evento(request.method, request.url.path, 200, {"filtros": filtros})
    return response


@app.post(
    "/v1/estadisticas/ventas",
    tags=["Estadísticas"],
    summary="Consultar estadísticas con filtros personalizados",
    description="Recibe un body JSON con consultas y calcula las estadísticas sobre el dataset cargado desde archivos CSV/Parquet. No usa una base de datos.",
    responses={
        200: {"description": "Estadísticas calculadas correctamente."},
        400: {"description": "Error de validación de filtros o body."},
        500: {"description": "Error interno del servidor."},
    },
)
def post_estadisticas(payload: dict[str, Any] | None, request: Request) -> dict[str, Any]:
    payload = payload or {}
    consultas = payload.get("consultas")
    filtros, _ = build_query_filter(consultas)
    df = bootstrap_dataset()
    response = build_service_response(df, request.method, filtros)
    registrar_sesion_evento(request.method, request.url.path, 200, {"filtros": filtros})
    return response


@app.get(
    "/v1/estadisticas/ventas/opciones",
    tags=["Estadísticas"],
    summary="Listar valores disponibles para los filtros",
    description="Devuelve valores disponibles para los filtros de género, canal, local y rango de fechas. Útil para construir listas en la interfaz.",
)
def opciones_filtros() -> dict[str, Any]:
    df = bootstrap_dataset()
    return obtener_opciones_filtros(df)


def _inject_enums_into_openapi(schema: dict[str, Any], options: dict[str, Any]) -> None:
    path = "/v1/estadisticas/ventas"
    try:
        paths = schema.get("paths", {})
        if path not in paths:
            return
        get_params = paths[path].get("get", {}).get("parameters", [])
        for param in get_params:
            name = param.get("name")
            # Instead of forcing an enum (which renders a select), provide
            # the available options in the parameter description so the UI
            # keeps a free-text input and shows suggestions.
            if name == "genero":
                opts = options.get("GENERO", [])
                sugest = "Sugerencias: " + ", ".join(str(x) for x in opts) if opts else ""
                desc = param.get("description", "")
                param["description"] = (sugest + ("\n" + desc if desc else "")).strip()
            if name == "canal":
                opts = options.get("CANAL", [])
                sugest = "Sugerencias: " + ", ".join(str(x) for x in opts) if opts else ""
                desc = param.get("description", "")
                param["description"] = (sugest + ("\n" + desc if desc else "")).strip()
            if name == "local":
                opts = options.get("LOCAL", [])
                sugest = "Sugerencias: " + ", ".join(str(x) for x in opts[:100]) if opts else ""
                desc = param.get("description", "")
                param["description"] = (sugest + ("\n" + desc if desc else "")).strip()
            if name in {"fecha_desde", "fecha_hasta"}:
                desc = param.get("description", "")
                fecha_desde = options.get("FECHA_DESDE")
                fecha_hasta = options.get("FECHA_HASTA")
                range_text = f" Rango: {fecha_desde} — {fecha_hasta}" if fecha_desde and fecha_hasta else ""
                param["description"] = (desc + range_text).strip()
    except Exception:
        # don't fail OpenAPI generation on any error
        return


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    try:
        df = bootstrap_dataset()
        options = obtener_opciones_filtros(df)
        _inject_enums_into_openapi(openapi_schema, options)
    except Exception:
        # best-effort: if dataset not available, leave schema as-is
        pass
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
