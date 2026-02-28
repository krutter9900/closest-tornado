import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")

from api.app.import_noaa_year import latest_details_files_by_year, make_linestring_wkt, parse_dt


class ImportUtilsTests(unittest.TestCase):
    def test_parse_dt_formats(self):
        self.assertEqual(parse_dt("01-Jan-13 05:30:00"), "2013-01-01T05:30:00")
        self.assertEqual(parse_dt("2013-01-01 05:30:00"), "2013-01-01T05:30:00")

    def test_linestring_handles_missing_end(self):
        wkt = make_linestring_wkt(-97.5, 35.4, None, None)
        self.assertEqual(wkt, "LINESTRING(-97.5 35.4, -97.5 35.4)")


    def test_latest_details_files_by_year_selects_latest_revision(self):
        listing = """
        StormEvents_details-ftp_v1.0_d2020_c20240210.csv.gz
        StormEvents_details-ftp_v1.0_d2020_c20240222.csv.gz
        StormEvents_details-ftp_v1.0_d2021_c20240105.csv.gz
        """
        with patch("api.app.import_noaa_year.subprocess.check_output", return_value=listing):
            result = latest_details_files_by_year(start_year=2020, end_year=2021)

        self.assertEqual(result[2020]["revision"], "20240222")
        self.assertEqual(result[2021]["filename"], "StormEvents_details-ftp_v1.0_d2021_c20240105.csv.gz")


if __name__ == "__main__":
    unittest.main()
