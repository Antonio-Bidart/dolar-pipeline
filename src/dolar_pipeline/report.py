from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from pathlib import Path

from .database import latest_rates


def build_html_report(connection: sqlite3.Connection, report_path: Path) -> int:
    rows = latest_rates(connection)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    table_rows = "\n".join(_render_row(row) for row in rows)
    observed_dates = sorted({row["observed_date"] for row in rows})
    observed_date = ", ".join(observed_dates) if observed_dates else "sin datos"

    report_path.write_text(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dolar Pipeline - Ultimas cotizaciones</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f6f7f9;
      color: #182026;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
    }}
    .meta {{
      margin: 0 0 24px;
      color: #52606d;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      border: 1px solid #d8dee4;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid #e6ebf0;
      text-align: left;
    }}
    th {{
      background: #0f766e;
      color: white;
      font-size: 13px;
      text-transform: uppercase;
    }}
    td.number {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .empty {{
      padding: 20px;
      background: white;
      border: 1px solid #d8dee4;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Dolar Pipeline</h1>
    <p class="meta">Ultima cotizacion disponible por mercado. Fechas observadas: {html.escape(observed_date)}. Reporte generado: {html.escape(generated_at)}.</p>
    {_render_table(table_rows) if rows else '<p class="empty">Todavia no hay registros para mostrar.</p>'}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return len(rows)


def _render_table(table_rows: str) -> str:
    return f"""<table>
      <thead>
        <tr>
          <th>Casa</th>
          <th>Nombre</th>
          <th>Compra</th>
          <th>Venta</th>
          <th>Actualizacion API</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>"""


def _render_row(row: sqlite3.Row) -> str:
    compra = _money(row["compra"])
    venta = _money(row["venta"])
    return f"""<tr>
      <td>{html.escape(row["casa"])}</td>
      <td>{html.escape(row["nombre"])}</td>
      <td class="number">{compra}</td>
      <td class="number">{venta}</td>
      <td>{html.escape(row["fecha_actualizacion"])}</td>
    </tr>"""


def _money(value: float | None) -> str:
    if value is None:
        return "-"
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
