import unittest
from datetime import datetime

from pydantic import ValidationError

from api.app.schemas import ClosestTornadoRequest


class SchemaTests(unittest.TestCase):
    def test_address_whitespace_normalized(self):
        payload = ClosestTornadoRequest(address="  123  Main St   Oklahoma City  ")
        self.assertEqual(payload.address, "123 Main St Oklahoma City")

    def test_address_rejects_control_chars(self):
        with self.assertRaises(ValidationError):
            ClosestTornadoRequest(address="123 Main St\n\x00")

    def test_units_default(self):
        payload = ClosestTornadoRequest(address="123 Main St, Tulsa, OK")
        self.assertEqual(payload.units, "miles")

    def test_top_n_default_and_validation(self):
        payload = ClosestTornadoRequest(address="123 Main St, Tulsa, OK")
        self.assertEqual(payload.top_n, 5)

        with self.assertRaises(ValidationError):
            ClosestTornadoRequest(address="123 Main St, Tulsa, OK", top_n=7)

    def test_year_range_defaults_and_validation(self):
        payload = ClosestTornadoRequest(address="123 Main St, Tulsa, OK")
        self.assertEqual(payload.start_year, 1950)
        self.assertEqual(payload.end_year, datetime.utcnow().year)

        with self.assertRaises(ValidationError):
            ClosestTornadoRequest(address="123 Main St, Tulsa, OK", start_year=2000, end_year=1999)

        with self.assertRaises(ValidationError):
            ClosestTornadoRequest(address="123 Main St, Tulsa, OK", end_year=datetime.utcnow().year + 1)


if __name__ == "__main__":
    unittest.main()
