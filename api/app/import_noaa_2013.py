import csv
import os
from sqlalchemy import create_engine, text

CSV_PATH = "/data/StormEvents_details-ftp_v1.0_d2013_c20250520.csv"

NEEDED = [
    "EVENT_ID", "EPISODE_ID", "STATE", "CZ_NAME", "WFO",
    "BEGIN_DATE_TIME", "END_DATE_TIME", "EVENT_TYPE",
    "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH",
    "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON",
]

engine = create_engine(os.environ["DATABASE_URL"])

INSERT_SQL = text("""
INSERT INTO tornado_event (
  event_id, begin_dt, end_dt, state, cz_name, wfo,
  tor_f_scale, tor_length_miles, tor_width_yards,
  begin_lat, begin_lon, end_lat, end_lon,
  geom_line, geog_line
)
VALUES (
  :event_id, :begin_dt, :end_dt, :state, :cz_name, :wfo,
  :tor_f_scale, :tor_length_miles, :tor_width_yards,
  :begin_lat, :begin_lon, :end_lat, :end_lon,
  ST_SetSRID(
    CASE
      WHEN :end_lat IS NULL OR :end_lon IS NULL THEN ST_MakeLine(ST_Point(:begin_lon, :begin_lat), ST_Point(:begin_lon, :begin_lat))
      ELSE ST_MakeLine(ST_Point(:begin_lon, :begin_lat), ST_Point(:end_lon, :end_lat))
    END,
    4326
  ),
  ST_SetSRID(
    CASE
      WHEN :end_lat IS NULL OR :end_lon IS NULL THEN ST_MakeLine(ST_Point(:begin_lon, :begin_lat), ST_Point(:begin_lon, :begin_lat))
      ELSE ST_MakeLine(ST_Point(:begin_lon, :begin_lat), ST_Point(:end_lon, :end_lat))
    END,
    4326
  )::geography
)
ON CONFLICT (event_id) DO NOTHING;
""")

def fnum(x):
    x = (x or "").strip()
    return float(x) if x else None

def inum(x):
    x = (x or "").strip()
    return int(float(x)) if x else None

def tstamp(x):
    x = (x or "").strip()
    return x if x else None

def main():
    inserted = 0

    with engine.begin() as conn:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)

            missing = [k for k in NEEDED if k not in (r.fieldnames or [])]
            if missing:
                raise SystemExit(f"Missing expected columns in NOAA file: {missing}")

            for row in r:
                if row.get("EVENT_TYPE") != "Tornado":
                    continue

                begin_lat = fnum(row.get("BEGIN_LAT"))
                begin_lon = fnum(row.get("BEGIN_LON"))
                if begin_lat is None or begin_lon is None:
                    continue

                params = {
                    "event_id": int(row["EVENT_ID"]),
                    "begin_dt": tstamp(row.get("BEGIN_DATE_TIME")),
                    "end_dt": tstamp(row.get("END_DATE_TIME")),
                    "state": (row.get("STATE") or None),
                    "cz_name": (row.get("CZ_NAME") or None),
                    "wfo": (row.get("WFO") or None),
                    "tor_f_scale": (row.get("TOR_F_SCALE") or None),
                    "tor_length_miles": fnum(row.get("TOR_LENGTH")),
                    "tor_width_yards": inum(row.get("TOR_WIDTH")),
                    "begin_lat": begin_lat,
                    "begin_lon": begin_lon,
                    "end_lat": fnum(row.get("END_LAT")),
                    "end_lon": fnum(row.get("END_LON")),
                }
                conn.execute(INSERT_SQL, params)
                inserted += 1

    print(f"Inserted tornado rows (attempted): {inserted}")

if __name__ == "__main__":
    main()