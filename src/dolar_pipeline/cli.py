from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .client import DolarApiClient, DolarApiError
from .config import SETTINGS
from .database import (
    connect,
    export_latest_csv,
    finish_run,
    init_db,
    latest_rates,
    start_run,
    upsert_quotes,
)
from .logging_utils import print_event, write_event
from .models import normalize_quotes
from .report import build_html_report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_pipeline(args)
    if args.command == "status":
        return check_status()
    if args.command == "report":
        return generate_report(args)
    if args.command == "latest":
        return show_latest(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dolar-pipeline",
        description="Ingesta automatizada de cotizaciones del dolar argentino desde DolarAPI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Ejecuta el pipeline completo.")
    run.add_argument("--db", type=Path, default=SETTINGS.default_db_path)
    run.add_argument("--log", type=Path, default=SETTINGS.default_log_path)
    run.add_argument("--csv", type=Path, default=SETTINGS.default_csv_path)
    run.add_argument("--report", type=Path, default=SETTINGS.default_report_path)
    run.add_argument("--skip-status-check", action="store_true")

    report = subparsers.add_parser("report", help="Regenera el reporte HTML desde SQLite.")
    report.add_argument("--db", type=Path, default=SETTINGS.default_db_path)
    report.add_argument("--report", type=Path, default=SETTINGS.default_report_path)

    latest = subparsers.add_parser("latest", help="Muestra la ultima tanda guardada.")
    latest.add_argument("--db", type=Path, default=SETTINGS.default_db_path)

    subparsers.add_parser("status", help="Consulta el estado de DolarAPI.")
    return parser


def run_pipeline(args: argparse.Namespace) -> int:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    endpoint = f"{SETTINGS.api_base_url}{SETTINGS.dollars_endpoint}"
    client = DolarApiClient()

    with connect(args.db) as connection:
        init_db(connection)
        start_run(connection, run_id, started_at, endpoint)

        event_base = {"run_id": run_id, "component": "dolar_pipeline"}
        write_event(args.log, {**event_base, "event": "run_started", "endpoint": endpoint})

        try:
            if not args.skip_status_check:
                status_payload = client.fetch_status()
                write_event(args.log, {**event_base, "event": "api_status", "payload": status_payload})

            raw_quotes = client.fetch_dollars()
            quotes = normalize_quotes(raw_quotes)
            result = upsert_quotes(connection, quotes, SETTINGS.source_name)
            csv_rows = export_latest_csv(connection, args.csv)
            report_rows = build_html_report(connection, args.report)
            finish_run(connection, run_id, "success", result=result)

            event = {
                **event_base,
                "event": "run_finished",
                "status": "success",
                "records_fetched": result.fetched,
                "records_inserted": result.inserted,
                "records_updated": result.updated,
                "records_skipped": result.skipped,
                "csv_rows": csv_rows,
                "report_rows": report_rows,
                "db_path": str(args.db),
                "csv_path": str(args.csv),
                "report_path": str(args.report),
            }
            write_event(args.log, event)
            print_event(event)
            return 0
        except (DolarApiError, ValueError) as exc:
            finish_run(connection, run_id, "failed", error_message=str(exc))
            event = {
                **event_base,
                "event": "run_finished",
                "status": "failed",
                "error": str(exc),
            }
            write_event(args.log, event)
            print_event(event)
            return 1


def check_status() -> int:
    try:
        payload = DolarApiClient().fetch_status()
    except DolarApiError as exc:
        print_event({"status": "failed", "error": str(exc)})
        return 1
    print_event({"status": "success", "payload": payload})
    return 0


def generate_report(args: argparse.Namespace) -> int:
    with connect(args.db) as connection:
        init_db(connection)
        rows = build_html_report(connection, args.report)
    print_event({"status": "success", "report_path": str(args.report), "rows": rows})
    return 0


def show_latest(args: argparse.Namespace) -> int:
    with connect(args.db) as connection:
        init_db(connection)
        rows = latest_rates(connection)

    if not rows:
        print("No hay cotizaciones guardadas todavia.")
        return 0

    for row in rows:
        compra = row["compra"] if row["compra"] is not None else "-"
        venta = row["venta"] if row["venta"] is not None else "-"
        print(f'{row["observed_date"]} | {row["casa"]:<16} | compra={compra} | venta={venta}')
    return 0


if __name__ == "__main__":
    sys.exit(main())

