# Dolar Pipeline

Pipeline de automatizacion para capturar cotizaciones del dolar argentino desde [DolarAPI](https://dolarapi.com/docs/argentina/operations/get-dolares), guardarlas en SQLite y dejar evidencia operativa de cada corrida.

El proyecto esta pensado como muestra tecnica para una busqueda de **Automations & Software Developer**: replica la logica de un flujo N8N/Make/Zapier, pero implementada en Python y GitHub Actions.

## Que demuestra

- **Disparador programado:** GitHub Actions ejecuta el pipeline de lunes a viernes a las 09:00 de Argentina.
- **Consumo de API REST:** integra `GET /v1/dolares` y opcionalmente `GET /v1/estado` de DolarAPI.
- **Base relacional:** persiste datos en SQLite con esquema versionable y consultas simples.
- **Idempotencia:** usa clave unica `(observed_date, casa, source)` para evitar duplicados si corre dos veces el mismo dia.
- **Observabilidad:** registra cada corrida en tabla `runs` y en logs JSON Lines (`logs/runs.ndjson`).
- **Replicabilidad:** no requiere credenciales ni dependencias externas para correr localmente.
- **Salida accionable:** genera CSV y reporte HTML con la ultima cotizacion disponible por mercado.
- **Publicacion web:** cada corrida puede publicar el reporte en GitHub Pages.

## Arquitectura del flujo

```text
Schedule / manual run
        |
        v
Check API status
        |
        v
Fetch DolarAPI /v1/dolares
        |
        v
Normalize + validate payload
        |
        v
SQLite upsert idempotente
        |
        v
CSV + HTML report + structured logs
```

## Uso local

Requisitos: Python 3.11 o superior.

```bash
python -m unittest discover -s tests
PYTHONPATH=src python -m dolar_pipeline status
PYTHONPATH=src python -m dolar_pipeline run
PYTHONPATH=src python -m dolar_pipeline latest
```

Opcionalmente se puede instalar como paquete editable:

```bash
python -m pip install -e .
dolar-pipeline run
```

En Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m dolar_pipeline status
python -m dolar_pipeline run
python -m dolar_pipeline latest
```

Archivos generados:

- `data/dolar_rates.sqlite`: base SQLite con cotizaciones y corridas.
- `data/latest_rates.csv`: ultima cotizacion disponible por mercado.
- `data/latest_report.html`: reporte HTML simple.
- `logs/runs.ndjson`: eventos estructurados por corrida.

Cuando corre en GitHub Actions, el reporte queda publicado en GitHub Pages:

- `https://antonio-bidart.github.io/dolar-pipeline/`
- `https://antonio-bidart.github.io/dolar-pipeline/latest_rates.csv`

## Comandos

```bash
PYTHONPATH=src python -m dolar_pipeline run --db data/dolar_rates.sqlite --csv data/latest_rates.csv --report data/latest_report.html
PYTHONPATH=src python -m dolar_pipeline report
PYTHONPATH=src python -m dolar_pipeline latest
```

## Modelo de datos

Tabla `rates`:

- `observed_date`: fecha de la cotizacion en Argentina.
- `casa`: mercado informado por la API (`oficial`, `blue`, `bolsa`, etc.).
- `compra`, `venta`: valores numericos.
- `fecha_actualizacion`: timestamp original de DolarAPI.
- `source`: origen del dato.
- `payload_hash`: hash del payload normalizado para detectar cambios.

Tabla `runs`:

- `run_id`, `started_at`, `finished_at`, `status`.
- contadores de `records_fetched`, `records_inserted`, `records_updated`, `records_skipped`.
- `error_message` si la corrida falla.

## Decision tecnica clave: idempotencia

El pipeline puede correrse manualmente varias veces en el mismo dia. Si DolarAPI devuelve el mismo dato, el registro se marca como `skipped`. Si el mismo mercado actualiza su cotizacion durante el dia, el registro se actualiza y queda reflejado como `updated`. Asi se evita inflar la base con duplicados sin perder cambios reales.

## Mejoras posibles

- Enviar alertas por email o Google Chat cuando la brecha entre oficial y blue supere un umbral.
- Publicar el reporte HTML en GitHub Pages.
- Agregar una integracion con Google Sheets usando Apps Script o la API de Sheets.
- Incorporar un dashboard en Streamlit o Power BI leyendo desde SQLite/CSV.
