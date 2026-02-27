import csv
import os
from sqlalchemy import create_engine, text

DB = os.environ.get("DATABASE_URL", "postgresql+psycopg://tornado:tornado@localhost:5432/tornado")
engine = create_engine(DB)

def make_linestring(begin_lon, begin_lat, end_lon, end_lat):
    return f"LINESTRING({begin_lon} {begin_lat}, {end_lon} {end_lat})"

with engine.begin() as conn:
    with open("tornado_sample.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            geom_wkt = make_linestring(row["begin_lon"], row["begin_lat"], row["end_lon"], row["end_lat"])
            conn.execute(text("""
                INSERT INTO tornado_event (
                  event_id, begin_dt, end_dt, state, cz_name, wfo,
                  tor_f_scale, tor_length_miles, tor_width_yards,
                  begin_lat, begin_lon, end_lat, end_lon,
                  geom_line, geog_line
                )
                VALUES (
                  :event_id, :begin_dt::timestamp, :end_dt::timestamp, :state, :cz_name, :wfo,
                  :tor_f_scale, :tor_length_miles::numeric, :tor_width_yards::int,
                  :begin_lat::float, :begin_lon::float, :end_lat::float, :end_lon::float,
                  ST_GeomFromText(:geom_wkt, 4326),
                  ST_GeomFromText(:geom_wkt, 4326)::geography
                )
                ON CONFLICT (event_id) DO UPDATE SET
                  geom_line = EXCLUDED.geom_line,
                  geog_line = EXCLUDED.geog_line;
            """), {
                "event_id": int(row["event_id"]),
                "begin_dt": row["begin_dt"],
                "end_dt": row["end_dt"],
                "state": row["state"],
                "cz_name": row["cz_name"],
                "wfo": row["wfo"],
                "tor_f_scale": row["tor_f_scale"],
                "tor_length_miles": row["tor_length_miles"],
                "tor_width_yards": row["tor_width_yards"],
                "begin_lat": row["begin_lat"],
                "begin_lon": row["begin_lon"],
                "end_lat": row["end_lat"],
                "end_lon": row["end_lon"],
                "geom_wkt": geom_wkt
            })

print("Ingest complete.")