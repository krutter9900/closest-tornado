import asyncio
import httpx
from .settings import settings

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def _geocode_census(address: str) -> dict:
    params = {
        "address": address,
        "benchmark": settings.census_benchmark,
        "vintage": settings.census_vintage,
        "format": "json",
    }

    # Retry on 5xx (like the 502 you saw)
    delays = [0.5, 1.0, 2.0, 4.0]
    async with httpx.AsyncClient(timeout=20.0) as client:
        for delay in [0.0] + delays:
            if delay:
                await asyncio.sleep(delay)

            r = await client.get(CENSUS_URL, params=params)
            if 500 <= r.status_code < 600:
                continue
            r.raise_for_status()

            data = r.json()
            matches = data.get("result", {}).get("addressMatches", [])
            if not matches:
                raise ValueError("NO_MATCH")

            best = matches[0]
            coords = best["coordinates"]
            return {
                "lat": float(coords["y"]),
                "lon": float(coords["x"]),
                "match_type": best.get("matchType"),
                "provider": "us_census",
            }

    raise ValueError("Census geocoder temporarily unavailable.")

async def _geocode_nominatim(query: str) -> dict:
    # Nominatim requires an identifying User-Agent; email param is supported. :contentReference[oaicite:1]{index=1}
    headers = {"User-Agent": settings.nominatim_user_agent}
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "countrycodes": "us",
    }
    if settings.nominatim_email:
        params["email"] = settings.nominatim_email

    # Be gentle: small retry + brief spacing to avoid hammering
    delays = [0.5, 1.0, 2.0]
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        for delay in [0.0] + delays:
            if delay:
                await asyncio.sleep(delay)

            r = await client.get(NOMINATIM_URL, params=params)
            if 500 <= r.status_code < 600:
                continue
            r.raise_for_status()

            data = r.json()
            if not data:
                raise ValueError("No geocoding match found for that input.")

            best = data[0]
            return {
                "lat": float(best["lat"]),
                "lon": float(best["lon"]),
                "match_type": best.get("type"),
                "provider": "nominatim",
            }

    raise ValueError("Nominatim temporarily unavailable.")

async def geocode_oneline(address: str) -> dict:
    # 1) Try Census first (best for full street addresses)
    try:
        return await _geocode_census(address)
    except ValueError as e:
        # NO_MATCH: fall back; other errors: also fall back to keep UX smooth
        pass

    # 2) Fall back to Nominatim (better for “city, state”, ZIP, place names)
    return await _geocode_nominatim(address)