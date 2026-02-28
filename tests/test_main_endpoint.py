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

    def first(self):
        return {
            "event_id": 1,
            "center_m": 1609.344,
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
        }


class FakeConn:
    def execute(self, *args, **kwargs):
        return FakeResult()


@contextmanager
def fake_begin():
    yield FakeConn()


class EndpointTests(unittest.TestCase):
    def test_units_selection(self):
        with patch.object(main, "run_migrations", lambda: None), patch.object(main, "geocode_oneline", AsyncMock(return_value={"lat": 35.4, "lon": -97.5, "provider": "test", "match_type": "rooftop"})), patch.object(main.engine, "begin", fake_begin):
            with TestClient(main.app) as client:
                res = client.post("/closest-tornado", json={"address": "123 Main St, Oklahoma City, OK", "units": "km"})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["result"]["selected_unit"], "km")
                self.assertAlmostEqual(data["result"]["selected_distance"], 1.609344, places=6)


    def test_admin_refresh_requires_token(self):
        with patch.object(main, "run_migrations", lambda: None), patch.object(main.settings, "admin_refresh_token", "secret"), patch.object(main, "refresh_updates", return_value=[]):
            with TestClient(main.app) as client:
                res = client.post("/admin/refresh-noaa")
                self.assertEqual(res.status_code, 401)

                ok = client.post("/admin/refresh-noaa", headers={"Authorization": "Bearer secret"})
                self.assertEqual(ok.status_code, 200)
                self.assertEqual(ok.json()["updated_years"], 0)


if __name__ == "__main__":
    unittest.main()
