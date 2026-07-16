# Cruz Morada - Servicio REST de estadísticas de ventas

Este proyecto implementa un servicio REST para consultar resúmenes estadísticos sobre ventas, cumpliendo con el enunciado del trabajo práctico. La lógica actual está centrada en tres componentes principales:

- carga y validación del archivo CSV de ventas,
- generación de un dataset parquet listo para consultar,
- exposición de una API FastAPI con endpoints GET y POST.

## Estructura actual del proyecto

```text
trabajo analisis/
|-- data/
|   |-- ventas_completas.csv
|   |-- transacciones_prueba.csv
|   `-- datos.json
|-- scripts/
|   |-- api.py
|   |-- api_service.py
|   |-- procesar_paralelo.py
|   |-- run_pipeline.py
|   |-- validacion.py
|-- main.py
|-- requirements.txt
|-- README.md
```

## Qué hace el proyecto hoy

- Lee un archivo CSV de ventas y lo valida por filas.
- Usa procesamiento por chunks y un executor paralelo para acelerar la validación.
- Genera un dataset intermedio en formato parquet para consultas rápidas.
- Expone una API REST con Swagger en FastAPI.
- Permite aplicar los filtros soportados por el enunciado: GENERO, EDAD, CANAL, CODIGO_PRODUCTO, ID_PERSONA, LOCAL, FECHA_DESDE y FECHA_HASTA.
- Ha sido verificado con el archivo completo [data/ventas_completas.csv](data/ventas_completas.csv), cargando 3.242.878 registros correctamente.
- En la implementación actual no se usa una base de datos; la API lee y procesa los datos desde archivos CSV/Parquet almacenados en la carpeta [data](data).

## Requisitos

```bash


```

## Paso a paso para ejecutar el programa

1. Instala las dependencias:

```bash
pip install -r requirements.txt
```

2. Desde la carpeta del proyecto, levanta la API:

```bash
python main.py
```

Detener y reiniciar el servidor local
----------------------------------

Si necesitas detener el servidor que está escuchando en el puerto `8000`, puedes usar estos comandos en PowerShell:

```powershell
# Ver procesos que usan el puerto 8000
netstat -ano | findstr :8000

# Matar un PID concreto (reemplaza <PID> por el obtenido arriba)
taskkill /PID <PID> /F

# Reiniciar la API (con recarga automática durante desarrollo)
python -m uvicorn scripts.api:app --host 0.0.0.0 --port 8000 --reload

# Alternativa (arranca mediante main.py)
python main.py
```

Si prefieres no matar procesos manualmente, cierra la terminal donde se está ejecutando la API y vuelve a arrancarla con el comando anterior.

3. La API queda disponible en:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc



## Endpoints disponibles

> La documentación interactiva de Swagger se genera automáticamente en /docs. Allí se explicita que la API trabaja sobre archivos en disco y no sobre una base de datos persistente.

Nota sobre Swagger/UI
---------------------

En la documentación Swagger (`/docs`) los parámetros de consulta se muestran
como campos de texto libres (no como selects). Para ayudar al usuario, la API
inyecta las opciones disponibles (recuperadas por `/v1/estadisticas/ventas/opciones`)
en la *descripción* de cada parámetro como una lista de sugerencias. Esto
permite que el desarrollador vea rápidamente valores válidos sin forzar un
comportamiento de select en la UI.

Si prefieres una experiencia interactiva integrada (autocompletado con selección
en la propia UI), dímelo y lo integramos mediante un pequeño script estático
que extienda Swagger UI.

### GET /v1/estadisticas/ventas

Consulta estadística general o filtrada mediante query params.

Ejemplo:

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?canal=POS"
```

### POST /v1/estadisticas/ventas

Consulta estadística con filtros personalizados enviados en el body JSON.

Ejemplos:

```bash
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{"consultas": [{"consulta": "GENERO", "valor": "Femenino"}, {"consulta": "CANAL", "valor": "POS"}]}'
```

```bash
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{"consultas": [{"consulta": "LOCAL", "valor": "209"}, {"consulta": "FECHA_DESDE", "valor": "2026-01-01T00:00:00"}]}'
```

## Filtros soportados

Además del ingreso manual de valores, la API expone la ruta /v1/estadisticas/ventas/opciones para consultar los valores disponibles de los filtros de género, canal, local y el rango de fechas del dataset.

Ejemplos rápidos usando `/opciones` y los filtros
-------------------------------------------------

1) Obtener las opciones disponibles (GENERO, CANAL, LOCAL y rango de fechas):

```bash
curl -s http://127.0.0.1:8000/v1/estadisticas/ventas/opciones | jq .
```

Respuesta de ejemplo (simplificada):

```json
{
  "GENERO": ["No especificado","Masculino","Femenino","Otro"],
  "CANAL": ["APP","CCT","POS","WEB"],
  "LOCAL": [3,5,6,9,11,15,...],
  "FECHA_DESDE": "2023-11-09T13:16:36",
  "FECHA_HASTA": "2024-12-02T19:54:49"
}
```

2) Usar las opciones para formar una consulta GET (ejemplo: filtrar por `genero` y `local`):

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?genero=Femenino&local=209"
```

3) Usar las opciones en una consulta POST (ejemplo con CANAL y FECHA_DESDE):

```bash
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{"consultas": [{"consulta": "CANAL", "valor": "POS"}, {"consulta": "FECHA_DESDE", "valor": "2024-01-01T00:00:00"}] }'
```


El servicio solo implementa los filtros textualmente exigidos por el enunciado:

- GENERO: "No especificado", "Masculino", "Femenino" o "Otro"
- EDAD: número entero
- CANAL: POS, WEB, APP, CCT, APR o WPR
- CODIGO_PRODUCTO: identificador único del producto
- ID_PERSONA: código UUID que identifica a un cliente
- LOCAL: número de local
- FECHA_DESDE: fecha inicial en formato ISO-8601
- FECHA_HASTA: fecha final en formato ISO-8601

No se añaden filtros adicionales fuera de esta lista.

Ejemplos de uso:

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?genero=Femenino&local=209"
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{"consultas": [{"consulta": "CANAL", "valor": "POS"}, {"consulta": "FECHA_DESDE", "valor": "2026-01-01T00:00:00"}]}'
```

## Control de errores

El servicio cumple con el formato de error solicitado en el enunciado.

### Formato de respuesta de error

```json
{
  "detail": "Descripción detallada del error",
  "instance": "/v1/estadisticas/ventas",
  "status": 400,
  "title": "Bad Request",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
  "timestamp": "2026-06-30T20:44:49.201437123Z",
  "errorCode": "VF",
  "errorLabel": "Validación Fallida",
  "method": "POST"
}
```

### Casos cubiertos

- Código 400: la lista de consultas viene vacía o nula.
- Código 400: la consulta no pertenece a los filtros soportados.
- Código 400: el valor no es convertible al tipo esperado (por ejemplo, un texto no numérico para LOCAL o EDAD).
- Código 400: la fecha inicial es posterior a la fecha final.
- Código 500: error interno del servidor al calcular o procesar la respuesta.

### Ejemplos

```bash
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{}'
```

Respuesta esperada: error 400 con `errorCode: VF` y `errorLabel: Validación Fallida`.

## Preparar el dataset

```bash
python scripts/run_pipeline.py --input data/transacciones_prueba.csv --workers 2 --executor thread --sample 200
```

## Prueba simple con el dataset completo

Se puede ejecutar una verificación rápida sobre el archivo completo de ventas para comprobar que la carga, el preprocesamiento y el cálculo de estadísticas funcionan correctamente:

```bash
C:/Users/amaru/AppData/Local/Programs/Python/Python313/python.exe -c "from pathlib import Path; from scripts.api_service import load_dataset, build_service_response; input_path = Path('data/ventas_completas.csv'); out_path = Path('data/ventas_api.parquet'); df = load_dataset(input_path, out_path); print('rows', len(df)); print('monto_aplicado_mean', float(df['MONTO APLICADO'].mean())); stats = build_service_response(df, 'GET', {}); print(stats)"
```

Resultado esperado: carga de 3.242.878 filas y generación de estadísticas resumidas sin errores.

## Datos de ejemplo

El archivo [data/datos.json](data/datos.json) contiene un payload de ejemplo para probar el endpoint POST.

## Componentes principales

### [scripts/validacion.py](scripts/validacion.py)

Contiene las reglas de validación de cada transacción:

- cantidad correcta de columnas,
- campos obligatorios no vacíos,
- enteros válidos para SKU, unidades, boleta y local,
- montos y descuentos válidos,
- RUT y UUID válidos,
- fechas válidas,
- edad calculada y rango plausible,
- género dentro del dominio esperado.

### [scripts/procesar_paralelo.py](scripts/procesar_paralelo.py)

Implementa la carga por chunks del CSV y la validación paralela. Cada worker procesa un bloque de filas y devuelve resultados al proceso principal, que es quien escribe el dataset y el log de descartes.

### [scripts/api_service.py](scripts/api_service.py)

Centraliza la lógica de negocio de la API:

- carga del dataset,
- validación de filtros,
- aplicación de filtros,
- cálculo de estadísticas resumidas.

### [scripts/api.py](scripts/api.py)

Expone la API FastAPI con los endpoints GET y POST, además de los manejadores de errores en el formato solicitado.

### [main.py](main.py)

Arranca la aplicación con Uvicorn, cargando el dataset al iniciar.

## Notas de funcionamiento

- El proyecto usa un dataset parquet generado automáticamente para acelerar las consultas.
- Los filtros se validan contra la lista soportada por el enunciado antes de aplicar la consulta.
- Si la lista de consultas viene vacía o nula, la API responde con un error 400.
- Si una consulta o un valor no es válido, la API responde con un error 400 con detalle claro.
- Si ocurre un fallo interno en el cálculo o el procesamiento, la API responde con un error 500 en el mismo formato.
- La carga del archivo completo [data/ventas_completas.csv](data/ventas_completas.csv) fue probada exitosamente en el entorno actual.

## Registro de ejecuciones y sesiones

El proyecto puede guardar registros simples en archivos de texto para auditar las pruebas y las consultas realizadas contra la API.

- Registros de pruebas: [data/logs/pruebas_api.log](data/logs/pruebas_api.log)
- Registros de sesión: [data/logs/sesion_api.log](data/logs/sesion_api.log)

Cada entrada se guarda en formato JSON por línea, con marca de tiempo, estado HTTP, nombre de la prueba o método/path consultado y el resultado asociado.

## Pruebas

Se incluye una batería básica de pruebas unitarias en [tests/test_api_service.py](tests/test_api_service.py).

Para ejecutarlas:

```bash
python -m pytest -q
```

Además, puedes ejecutar el script de pruebas funcionales en [scripts/pruebas_api.py](scripts/pruebas_api.py), que cubre:

- consultas sin filtros,
- combinaciones de filtros por columnas,
- casos de éxito por cada filtro,
- casos de error por cada filtro,
- y ejemplos de payloads inválidos.

```bash
python scripts/pruebas_api.py
```
