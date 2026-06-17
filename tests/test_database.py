import sqlite3
import unittest

from dolar_pipeline.database import init_db, latest_rates, upsert_quotes
from dolar_pipeline.models import normalize_quotes


RAW_QUOTES = [
    {
        "casa": "oficial",
        "nombre": "Oficial",
        "moneda": "USD",
        "compra": 1180,
        "venta": 1220,
        "fechaActualizacion": "2026-06-17T12:00:00.000Z",
    },
    {
        "casa": "blue",
        "nombre": "Blue",
        "moneda": "USD",
        "compra": 1210,
        "venta": 1230,
        "fechaActualizacion": "2026-06-17T12:00:00.000Z",
    },
]


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        init_db(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_upsert_is_idempotent_for_same_payload(self):
        quotes = normalize_quotes(RAW_QUOTES)

        first = upsert_quotes(self.connection, quotes, "dolarapi")
        second = upsert_quotes(self.connection, quotes, "dolarapi")

        self.assertEqual(first.inserted, 2)
        self.assertEqual(first.updated, 0)
        self.assertEqual(first.skipped, 0)
        self.assertEqual(second.inserted, 0)
        self.assertEqual(second.updated, 0)
        self.assertEqual(second.skipped, 2)

    def test_upsert_updates_when_same_day_quote_changes(self):
        first_payload = normalize_quotes(RAW_QUOTES)
        changed_payload = normalize_quotes(
            [
                {
                    **RAW_QUOTES[0],
                    "venta": 1225,
                }
            ]
        )

        upsert_quotes(self.connection, first_payload, "dolarapi")
        result = upsert_quotes(self.connection, changed_payload, "dolarapi")

        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 1)
        self.assertEqual(result.skipped, 0)

    def test_latest_rates_returns_most_recent_quote_per_market(self):
        upsert_quotes(self.connection, normalize_quotes(RAW_QUOTES), "dolarapi")
        upsert_quotes(
            self.connection,
            normalize_quotes(
                [
                    {
                        **RAW_QUOTES[0],
                        "fechaActualizacion": "2026-06-18T12:00:00.000Z",
                        "venta": 1240,
                    }
                ]
            ),
            "dolarapi",
        )

        rows = latest_rates(self.connection)
        by_casa = {row["casa"]: row for row in rows}

        self.assertEqual(len(rows), 2)
        self.assertEqual(by_casa["oficial"]["observed_date"], "2026-06-18")
        self.assertEqual(by_casa["oficial"]["venta"], 1240)
        self.assertEqual(by_casa["blue"]["observed_date"], "2026-06-17")


if __name__ == "__main__":
    unittest.main()
