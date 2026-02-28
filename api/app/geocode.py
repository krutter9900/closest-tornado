import asyncio

import httpx

from .settings import settings

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class GeocodingError(Exception):
    pass


class NoGeocodeMatchError(GeocodingError):
    pass


class GeocoderUnavailableError(GeocodingError):
    pass


async def _geocode_census(address: str) -> dict:
    params = {
        "address": address,
        "benchmark": settings.census_benchmark,
        "vintage": settings.census_vintage,
        "format": "json",
    }

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
                raise NoGeocodeMatchError("NO_MATCH")

            best = matches[0]
            coords = best["coordinates"]
            return {
                "lat": float(coords["y"]),
                "lon": float(coords["x"]),
                "match_type": best.get("matchType"),
                "provider": "us_census",
            }

    raise GeocoderUnavailableError("Census geocoder temporarily unavailable.")


async def _geocode_nominatim(query: str) -> dict:
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
                raise NoGeocodeMatchError("No geocoding match found for that input.")

            best = data[0]
            return {
                "lat": float(best["lat"]),
                "lon": float(best["lon"]),
                "match_type": best.get("type"),
                "provider": "nominatim",
            }

    raise GeocoderUnavailableError("Nominatim temporarily unavailable.")


async def geocode_oneline(address: str) -> dict:
    try:
        return await _geocode_census(address)
    except (NoGeocodeMatchError, GeocoderUnavailableError):
        return await _geocode_nominatim(address)
