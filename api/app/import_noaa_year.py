import csv
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
DATA_DIR = Path("/data")

engine = create_engine(os.environ["DATABASE_URL"])

# Build geometry from WKT to avoid NULL parameter typing issues in older years
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
  ST_GeomFromText(:geom_wkt, 4326),
  ST_GeomFromText(:geom_wkt, 4326)::geography
)
ON CONFLICT (event_id) DO NOTHING;
""")

NEEDED = [
    "EVENT_ID", "STATE", "CZ_NAME", "WFO",
    "BEGIN_DATE_TIME", "END_DATE_TIME", "EVENT_TYPE",
    "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH",
    "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON",
]


def fnum(x):
    x = (x or "").strip()
    return float(x) if x else None


def inum(x):
    x = (x or "").strip()
    return int(float(x)) if x else None


def parse_dt(s: str | None, source_year: int | None = None) -> str | None:
    s = (s or "").strip()
    if not s:
        return None

    # Common modern format in NOAA files
    for fmt in ("%d-%b-%y %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)

            # NOAA commonly stores two-digit years in older files. Python's %y
            # pivot (1969-2068) can map 1950s/1960s rows into the future.
            if fmt == "%d-%b-%y %H:%M:%S" and source_year is not None and dt.year > source_year + 1:
                dt = dt.replace(year=dt.year - 100)

            return dt.isoformat(sep="T")
        except ValueError:
            pass

    # If it already looks ISO-ish (sometimes)
    if "T" in s and ":" in s:
        return s

    # Give up gracefully (don’t break import)
    return None


def make_linestring_wkt(begin_lon, begin_lat, end_lon, end_lat) -> str:
    # If end is missing, make a zero-length line at the begin point
    if end_lon is None or end_lat is None:
        end_lon, end_lat = begin_lon, begin_lat
    return f"LINESTRING({begin_lon} {begin_lat}, {end_lon} {end_lat})"


def source_year_from_filename(csv_path: Path) -> int | None:
    match = re.search(r"_d(\d{4})_", csv_path.name)
    if match:
        return int(match.group(1))
    return None


def latest_details_filename(year: int) -> str:
    html = subprocess.check_output(["curl", "-s", BASE_URL], text=True)
    pattern = re.compile(rf"(StormEvents_details-ftp_v1\.0_d{year}_c(\d+)\.csv\.gz)")
    matches = pattern.findall(html)
    if not matches:
        raise SystemExit(f"No details file found for year {year} in NOAA directory listing.")
    matches.sort(key=lambda t: t[1], reverse=True)
    return matches[0][0]


def latest_details_files_by_year(start_year: int = 1950, end_year: int | None = None) -> dict[int, dict[str, str]]:
    """Return the newest NOAA details file per year using the cYYYYMMDD revision token."""
    if end_year is None:
        end_year = datetime.utcnow().year

    html = subprocess.check_output(["curl", "-s", BASE_URL], text=True)
    pattern = re.compile(r"(StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d+)\.csv\.gz)")

    latest: dict[int, dict[str, str]] = {}
    for filename, year_s, revision in pattern.findall(html):
        year = int(year_s)
        if year < start_year or year > end_year:
            continue

        existing = latest.get(year)
        if existing is None or revision > existing["revision"]:
            latest[year] = {"filename": filename, "revision": revision}

    return latest


def ensure_downloaded(year: int) -> Path:
    return ensure_downloaded_filename(latest_details_filename(year))


def ensure_downloaded_filename(gz_name: str) -> Path:
    csv_name = gz_name[:-3]  # strip .gz
    csv_path = DATA_DIR / csv_name
    if csv_path.exists():
        return csv_path

    gz_path = DATA_DIR / gz_name
    print(f"Downloading {gz_name} ...")
    subprocess.check_call(["curl", "-L", "-o", str(gz_path), BASE_URL + gz_name])
    subprocess.check_call(["gunzip", "-f", str(gz_path)])
    if not csv_path.exists():
        raise SystemExit(f"Expected CSV not found after gunzip: {csv_path}")
    return csv_path


def import_year(csv_path: Path) -> tuple[int, int]:
    attempted = 0
    inserted = 0
    source_year = source_year_from_filename(csv_path)
    with engine.begin() as conn:
        with open(csv_path, newline="", encoding="utf-8") as f:
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

                end_lat = fnum(row.get("END_LAT"))
                end_lon = fnum(row.get("END_LON"))
                geom_wkt = make_linestring_wkt(begin_lon, begin_lat, end_lon, end_lat)

                params = {
                    "event_id": int(row["EVENT_ID"]),
                    "begin_dt": parse_dt(row.get("BEGIN_DATE_TIME"), source_year=source_year),
                    "end_dt": parse_dt(row.get("END_DATE_TIME"), source_year=source_year),
                    "state": (row.get("STATE") or None),
                    "cz_name": (row.get("CZ_NAME") or None),
                    "wfo": (row.get("WFO") or None),
                    "tor_f_scale": (row.get("TOR_F_SCALE") or None),
                    "tor_length_miles": fnum(row.get("TOR_LENGTH")),
                    "tor_width_yards": inum(row.get("TOR_WIDTH")),
                    "begin_lat": begin_lat,
                    "begin_lon": begin_lon,
                    "end_lat": end_lat,
                    "end_lon": end_lon,
                    "geom_wkt": geom_wkt,
                }
                result = conn.execute(INSERT_SQL, params)
                attempted += 1
                inserted += int(result.rowcount or 0)
    return attempted, inserted


def main():
    if len(sys.argv) != 2:
        print("Usage: python import_noaa_year.py <YEAR>")
        raise SystemExit(2)

    year = int(sys.argv[1])
    csv_path = ensure_downloaded(year)
    attempted, inserted = import_year(csv_path)
    print(f"Imported tornado rows for {year}: attempted={attempted}, inserted={inserted}")


if __name__ == "__main__":
    main()
