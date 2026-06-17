import unittest

from dolar_pipeline.models import normalize_quotes


class NormalizeQuotesTest(unittest.TestCase):
    def test_normalizes_dolarapi_payload(self):
        quotes = normalize_quotes(
            [
                {
                    "casa": "BLUE",
                    "nombre": "Blue",
                    "moneda": "USD",
                    "compra": 1215,
                    "venta": 1235,
                    "fechaActualizacion": "2026-06-17T12:00:00.000Z",
                }
            ]
        )

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].casa, "blue")
        self.assertEqual(quotes[0].observed_date, "2026-06-17")
        self.assertEqual(quotes[0].venta, 1235.0)
        self.assertEqual(len(quotes[0].payload_hash), 64)

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            normalize_quotes([{"casa": "blue"}])


if __name__ == "__main__":
    unittest.main()

