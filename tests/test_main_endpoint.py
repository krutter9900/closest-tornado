import os
import unittest
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")

from fastapi.testclient import TestClient

from api.app import main


class FakeResult:
    def mappings(self):
        return self

    def _row(self, event_id: int, miles: float):
        center_m = miles * 1609.344
        return {
            "event_id": event_id,
            "center_m": center_m,
            "edge_m": None,
            "tor_f_scale": "EF1",
            "begin_dt": None,
            "end_dt": None,
            "state": "OK",
            "cz_name": "Oklahoma",
            "wfo": "OUN",
            "tor_length_miles": 1.2,
            "tor_width_yards": 100,
            "track_geojson": '{"type":"LineString","coordinates":[[-97.5,35.4],[-97.4,35.5]]}',
            "closest_pt_geojson": '{"type":"Point","coordinates":[-97.45,35.45]}',
            "corridor_geojson": '{"type":"Polygon","coordinates":[[[-97.5,35.4],[-97.4,35.4],[-97.4,35.5],[-97.5,35.5],[-97.5,35.4]]]}',
        }

    def first(self):
        return self._row(1, 1.0)

    def all(self):
        return [self._row(i, i * 1.0) for i in range(1, 6)]


class FakeConn:
    def execute(self, *args, **kwargs):
        return FakeResult()


@contextmanager
def fake_begin():
    yield FakeConn()


class EndpointTests(unittest.TestCase):
    def test_units_selection_and_top_results(self):
        with patch.object(main, "run_migrations", lambda: None), patch.object(main, "geocode_oneline", AsyncMock(return_value={"lat": 35.4, "lon": -97.5, "provider": "test", "match_type": "rooftop"})), patch.object(main.engine, "begin", fake_begin):
            with TestClient(main.app) as client:
                res = client.post("/closest-tornado", json={"address": "123 Main St, Oklahoma City, OK", "units": "km"})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["result"]["selected_unit"], "km")
                self.assertIn("share_url", data)
                self.assertEqual(len(data["top_results"]), 5)
                self.assertIn("corridor_geojson", data["top_results"][0])

    def test_lookup_by_coords(self):
        with patch.object(main, "run_migrations", lambda: None), patch.object(main.engine, "begin", fake_begin):
            with TestClient(main.app) as client:
                res = client.get("/closest-tornado-by-coords?lat=35.4&lon=-97.5&units=miles")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["query"]["provider"], "shared_link")
                self.assertEqual(len(data["top_results"]), 5)


if __name__ == "__main__":
    unittest.main()
