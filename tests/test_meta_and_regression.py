import json
import os
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")

from fastapi.testclient import TestClient

from api.app import main


class FakeMetaResult:
    def mappings(self):
        return self

    def first(self):
        return {
            "data_last_refreshed": datetime(2024, 1, 5, 10, 0, 0),
            "dataset_version": "20240105",
            "updated_at": datetime(2024, 1, 5, 10, 5, 0),
            "tornado_event_count": 123,
            "max_begin_dt": datetime(2023, 12, 31, 23, 0, 0),
        }


class FakeConn:
    def execute(self, *args, **kwargs):
        return FakeMetaResult()


@contextmanager
def fake_begin():
    yield FakeConn()


class MetaEndpointTests(unittest.TestCase):
    def test_meta_endpoint_contract(self):
        with patch.object(main, "run_migrations", lambda: None), patch.object(main.engine, "begin", fake_begin):
            with TestClient(main.app) as client:
                res = client.get("/meta")
                self.assertEqual(res.status_code, 200)
                payload = res.json()

        self.assertEqual(payload["dataset_version"], "20240105")
        self.assertEqual(payload["tornado_event_count"], 123)
        self.assertEqual(payload["data_last_refreshed"], "2024-01-05T10:00:00")
        self.assertIn("metadata_updated_at", payload)
        self.assertIn("latest_event_begin_dt", payload)


class RegressionDatasetTests(unittest.TestCase):
    def test_regression_cases(self):
        fixtures = Path("tests/regression_cases.json")
        cases = json.loads(fixtures.read_text(encoding="utf-8"))

        def fake_query_top_rows(lat, lon, limit=5):
            if (round(lat, 4), round(lon, 4)) == (35.4676, -97.5164):
                base_m = 1609.344
                event_id = 101
            else:
                base_m = 3000.0
                event_id = 202

            return [
                {
                    "event_id": event_id,
                    "center_m": base_m,
                    "edge_m": None,
                    "tor_f_scale": "EF1",
                    "begin_dt": None,
                    "end_dt": None,
                    "state": "OK",
                    "cz_name": "Test",
                    "wfo": "OUN",
                    "tor_length_miles": 1.0,
                    "tor_width_yards": 50,
                    "track_geojson": '{"type":"LineString","coordinates":[[-97.5,35.4],[-97.4,35.5]]}',
                    "closest_pt_geojson": '{"type":"Point","coordinates":[-97.45,35.45]}',
                    "corridor_geojson": None,
                }
            ]

        with patch.object(main, "run_migrations", lambda: None), patch.object(main, "_query_top_rows", side_effect=fake_query_top_rows):
            with TestClient(main.app) as client:
                for case in cases:
                    response = client.get(
                        "/closest-tornado-by-coords",
                        params={"lat": case["lat"], "lon": case["lon"], "units": case["units"]},
                    )
                    self.assertEqual(response.status_code, 200, case["name"])
                    result = response.json()["result"]
                    self.assertEqual(result["event_id"], case["expected_event_id"], case["name"])

                    if "expected_distance_miles" in case:
                        self.assertAlmostEqual(result["selected_distance"], case["expected_distance_miles"], places=6)
                    if "expected_distance_km" in case:
                        self.assertAlmostEqual(result["selected_distance"], case["expected_distance_km"], places=6)


if __name__ == "__main__":
    unittest.main()
