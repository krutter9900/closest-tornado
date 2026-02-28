import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")

from api.app.import_noaa_year import make_linestring_wkt, parse_dt


class ImportUtilsTests(unittest.TestCase):
    def test_parse_dt_formats(self):
        self.assertEqual(parse_dt("01-Jan-13 05:30:00"), "2013-01-01T05:30:00")
        self.assertEqual(parse_dt("2013-01-01 05:30:00"), "2013-01-01T05:30:00")

    def test_linestring_handles_missing_end(self):
        wkt = make_linestring_wkt(-97.5, 35.4, None, None)
        self.assertEqual(wkt, "LINESTRING(-97.5 35.4, -97.5 35.4)")


if __name__ == "__main__":
    unittest.main()
