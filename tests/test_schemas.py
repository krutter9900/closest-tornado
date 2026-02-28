import unittest

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


if __name__ == "__main__":
    unittest.main()
