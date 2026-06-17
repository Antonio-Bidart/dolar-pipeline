from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import DollarQuote


SCHEMA = """
CREATE TABLE IF NOT EXISTS rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_date TEXT NOT NULL,
    casa TEXT NOT NULL,
    nombre TEXT NOT NULL,
    moneda TEXT NOT NULL,
    compra REAL,
    venta REAL,
    fecha_actualizacion TEXT NOT NULL,
    source TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    inserted_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (observed_date, casa, source)
);

CREATE INDEX IF NOT EXISTS idx_rates_observed_date ON rates(observed_date);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
"""


@dataclass(frozen=True)
class UpsertResult:
    fetched: int
    inserted: int
    updated: int
    skipped: int


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def start_run(
    connection: sqlite3.Connection,
    run_id: str,
    started_at: str,
    endpoint: str,
) -> None:
    connection.execute(
        """
        INSERT INTO runs (run_id, started_at, status, endpoint)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, started_at, "running", endpoint),
    )
    connection.commit()


def finish_run(
    connection: sqlite3.Connection,
    run_id: str,
    status: str,
    result: UpsertResult | None = None,
    error_message: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    result = result or UpsertResult(fetched=0, inserted=0, updated=0, skipped=0)
    connection.execute(
        """
        UPDATE runs
        SET finished_at = ?,
            status = ?,
            records_fetched = ?,
            records_inserted = ?,
            records_updated = ?,
            records_skipped = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (
            finished_at,
            status,
            result.fetched,
            result.inserted,
            result.updated,
            result.skipped,
            error_message,
            run_id,
        ),
    )
    connection.commit()


def upsert_quotes(
    connection: sqlite3.Connection,
    quotes: Iterable[DollarQuote],
    source: str,
) -> UpsertResult:
    inserted = 0
    updated = 0
    skipped = 0
    fetched = 0
    now = datetime.now(timezone.utc).isoformat()

    with connection:
        for quote in quotes:
            fetched += 1
            current = connection.execute(
                """
                SELECT payload_hash
                FROM rates
                WHERE observed_date = ? AND casa = ? AND source = ?
                """,
                (quote.observed_date, quote.casa, source),
            ).fetchone()

            if current is None:
                connection.execute(
                    """
                    INSERT INTO rates (
                        observed_date, casa, nombre, moneda, compra, venta,
                        fecha_actualizacion, source, payload_hash, inserted_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quote.observed_date,
                        quote.casa,
                        quote.nombre,
                        quote.moneda,
                        quote.compra,
                        quote.venta,
                        quote.fecha_actualizacion,
                        source,
                        quote.payload_hash,
                        now,
                        now,
                    ),
                )
                inserted += 1
            elif current["payload_hash"] != quote.payload_hash:
                connection.execute(
                    """
                    UPDATE rates
                    SET nombre = ?,
                        moneda = ?,
                        compra = ?,
                        venta = ?,
                        fecha_actualizacion = ?,
                        payload_hash = ?,
                        updated_at = ?
                    WHERE observed_date = ? AND casa = ? AND source = ?
                    """,
                    (
                        quote.nombre,
                        quote.moneda,
                        quote.compra,
                        quote.venta,
                        quote.fecha_actualizacion,
                        quote.payload_hash,
                        now,
                        quote.observed_date,
                        quote.casa,
                        source,
                    ),
                )
                updated += 1
            else:
                skipped += 1

    return UpsertResult(fetched=fetched, inserted=inserted, updated=updated, skipped=skipped)


def latest_rates(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT r.observed_date, r.casa, r.nombre, r.moneda, r.compra, r.venta,
                   r.fecha_actualizacion, r.source
            FROM rates r
            WHERE NOT EXISTS (
                SELECT 1
                FROM rates newer
                WHERE newer.casa = r.casa
                  AND newer.source = r.source
                  AND (
                      newer.fecha_actualizacion > r.fecha_actualizacion
                      OR (
                          newer.fecha_actualizacion = r.fecha_actualizacion
                          AND newer.updated_at > r.updated_at
                      )
                  )
            )
            ORDER BY venta DESC, casa ASC
            """,
        )
    )


def export_latest_csv(connection: sqlite3.Connection, csv_path: Path) -> int:
    rows = latest_rates(connection)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "observed_date",
                "casa",
                "nombre",
                "moneda",
                "compra",
                "venta",
                "fecha_actualizacion",
                "source",
            ]
        )
        for row in rows:
            writer.writerow([row[key] for key in row.keys()])
    return len(rows)
