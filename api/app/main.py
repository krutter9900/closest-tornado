import json
import logging

from fastapi import FastAPI, HTTPException, Query, Request
from sqlalchemy import text

from .db import engine, run_migrations
from .geocode import GeocoderUnavailableError, NoGeocodeMatchError, geocode_oneline
from .guardrails import RateLimitConfig, SimpleRateLimiter, TTLCache
from .schemas import ClosestTornadoRequest, ClosestTornadoResponse
from .web import router as web_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Closest Tornado API", version="0.6.0")
app.include_router(web_router)

rate_limiter = SimpleRateLimiter(RateLimitConfig(max_requests=30, window_seconds=60))
result_cache = TTLCache(ttl_seconds=6 * 3600, max_items=5000)


@app.on_event("startup")
def _startup():
    run_migrations()


@app.get("/health")
def health():
    return {"ok": True}


def _notes_for_row(edge_m: float | None) -> list[str]:
    notes = [
        "Tracks are built from Storm Events begin/end points; the real ground path can differ.",
        "Geocoding uses U.S. Census first, with OpenStreetMap Nominatim fallback for non-street inputs.",
    ]
    if edge_m is not None:
        notes.append("Distance uses reported tornado width to estimate distance to the damage-path edge (width/2 buffer).")
    else:
        notes.append("Width was not available; distance is to the track centerline only.")
    return notes


def _serialize_row(row, units: str):
    center_m = float(row["center_m"])
    edge_m_val = row.get("edge_m")
    edge_m = float(edge_m_val) if edge_m_val is not None else None

    primary_m = edge_m if edge_m is not None else center_m
    dist_km = primary_m / 1000.0
    dist_miles = primary_m / 1609.344
    selected_distance = dist_miles if units == "miles" else dist_km
    distance_type = "estimated_damage_path_edge" if edge_m is not None else "centerline"

    return {
        "event_id": int(row["event_id"]),
        "distance_m": primary_m,
        "distance_miles": dist_miles,
        "distance_km": dist_km,
        "selected_unit": units,
        "selected_distance": selected_distance,
        "distance_type": distance_type,
        "tor_f_scale": row.get("tor_f_scale"),
        "begin_dt": row.get("begin_dt").isoformat() if row.get("begin_dt") else None,
        "end_dt": row.get("end_dt").isoformat() if row.get("end_dt") else None,
        "state": row.get("state"),
        "cz_name": row.get("cz_name"),
        "wfo": row.get("wfo"),
        "tor_length_miles": float(row["tor_length_miles"]) if row.get("tor_length_miles") is not None else None,
        "tor_width_yards": int(row["tor_width_yards"]) if row.get("tor_width_yards") is not None else None,
        "track_geojson": json.loads(row["track_geojson"]) if row["track_geojson"] else None,
        "closest_point_geojson": json.loads(row["closest_pt_geojson"]) if row["closest_pt_geojson"] else None,
        "corridor_geojson": json.loads(row["corridor_geojson"]) if row.get("corridor_geojson") else None,
        "notes": _notes_for_row(edge_m),
        "data_source": {
            "name": "NOAA NCEI Storm Events Database (Storm Data)",
            "coverage": "1950–present (updated periodically)",
        },
    }


def _query_top_rows(lat: float, lon: float, limit: int = 5):
    sql = text("""
    WITH user_pt AS (
      SELECT
        ST_SetSRID(ST_Point(:lon, :lat), 4326) AS geom,
        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography AS geog
    ),
    candidates AS (
      SELECT
        t.*,
        ST_Distance((SELECT geog FROM user_pt), t.geog_line) AS center_m,
        CASE
          WHEN t.tor_width_yards IS NULL THEN NULL
          ELSE GREATEST(
            0,
            ST_Distance((SELECT geog FROM user_pt), t.geog_line) - ((t.tor_width_yards * 0.9144) / 2.0)
          )
        END AS edge_m,
        ST_AsGeoJSON(t.geom_line) AS track_geojson,
        ST_AsGeoJSON(ST_ClosestPoint(t.geom_line, (SELECT geom FROM user_pt))) AS closest_pt_geojson,
        CASE
          WHEN t.tor_width_yards IS NULL THEN NULL
          ELSE ST_AsGeoJSON(
            ST_Buffer(
              t.geog_line,
              (t.tor_width_yards * 0.9144) / 2.0,
              'endcap=round join=round'
            )::geometry
          )
        END AS corridor_geojson
      FROM tornado_event t
      ORDER BY t.geog_line <-> (SELECT geog FROM user_pt)
      LIMIT 250
    ),
    ranked AS (
      SELECT *,
        COALESCE(edge_m, center_m) AS primary_m
      FROM candidates
    )
    SELECT *
    FROM ranked
    ORDER BY primary_m ASC
    LIMIT :limit;
    """)

    with engine.begin() as conn:
        return conn.execute(sql, {"lat": lat, "lon": lon, "limit": limit}).mappings().all()


def _build_response(lat: float, lon: float, provider: str, match_type: str | None, units: str, host_url: str):
    rows = _query_top_rows(lat, lon, limit=5)
    if not rows:
        raise HTTPException(status_code=404, detail="No tornado data loaded.")

    top_results = [_serialize_row(row, units) for row in rows]
    share_url = f"{host_url}?lat={lat:.6f}&lon={lon:.6f}&units={units}"
    return {
        "query": {
            "lat": lat,
            "lon": lon,
            "provider": provider,
            "match_type": match_type,
        },
        "result": top_results[0],
        "top_results": top_results,
        "share_url": share_url,
    }


@app.post("/closest-tornado", response_model=ClosestTornadoResponse)
async def closest_tornado(req: ClosestTornadoRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

    try:
        g = await geocode_oneline(req.address)
    except NoGeocodeMatchError:
        raise HTTPException(status_code=400, detail="No geocoding match found for that input.")
    except GeocoderUnavailableError:
        raise HTTPException(status_code=503, detail="Geocoding services are temporarily unavailable.")
    except Exception:
        logger.exception("Unexpected geocoding failure")
        raise HTTPException(status_code=500, detail="Unexpected error while geocoding.")

    lat, lon = g["lat"], g["lon"]
    lat_r = round(lat, 4)
    lon_r = round(lon, 4)
    cache_key = ("closest_v3", lat_r, lon_r, req.units)
    cached = result_cache.get(cache_key)
    if cached is not None:
        return cached

    response = _build_response(
        lat=lat,
        lon=lon,
        provider=g.get("provider", "unknown"),
        match_type=g.get("match_type"),
        units=req.units,
        host_url=str(request.base_url).rstrip("/"),
    )
    result_cache.set(cache_key, response)
    return response


@app.get("/closest-tornado-by-coords", response_model=ClosestTornadoResponse)
def closest_tornado_by_coords(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    units: str = Query("miles", pattern="^(miles|km)$"),
):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

    lat_r = round(lat, 4)
    lon_r = round(lon, 4)
    cache_key = ("closest_coords_v1", lat_r, lon_r, units)
    cached = result_cache.get(cache_key)
    if cached is not None:
        return cached

    response = _build_response(
        lat=lat,
        lon=lon,
        provider="shared_link",
        match_type=None,
        units=units,
        host_url=str(request.base_url).rstrip("/"),
    )
    result_cache.set(cache_key, response)
    return response
