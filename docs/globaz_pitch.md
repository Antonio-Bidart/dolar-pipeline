# Breve detalle para enviar junto al CV

Desarrolle un pipeline automatizado en Python para capturar cotizaciones del dolar argentino desde DolarAPI, persistirlas en SQLite y generar salidas operativas en CSV/HTML. El objetivo fue demostrar la logica completa de una automatizacion productiva: disparador programado, consumo de API REST, validacion de datos, persistencia relacional, idempotencia y observabilidad.

Puntos tecnicos relevantes:

- Integra una API REST publica sin credenciales (`GET /v1/dolares`) y valida el formato recibido antes de persistir.
- Guarda los datos en SQLite con clave unica por fecha, mercado y fuente para evitar duplicados si el flujo corre mas de una vez.
- Usa hash del payload para distinguir entre "dato repetido" y "dato actualizado".
- Registra cada corrida en una tabla `runs` y en logs JSON Lines, incluyendo registros insertados, actualizados, omitidos y errores.
- Incluye tests unitarios para normalizacion e idempotencia.
- Tiene un workflow de GitHub Actions que ejecuta tests y corre el pipeline automaticamente de lunes a viernes a las 09:00 de Argentina.

Este proyecto conecta con mi experiencia previa en automatizacion y mantenimiento de sistemas industriales en Ternium, y con mi formacion en Ciencia de Datos: ingesta, limpieza, trazabilidad, documentacion y comunicacion clara de resultados.

Repositorio sugerido: `dolar-pipeline`

