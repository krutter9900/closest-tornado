from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Any, Dict, List
import string


class ClosestTornadoRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=200)
    units: Literal["miles", "km"] = "miles"
    top_n: Literal[5, 10, 15] = 5
    start_year: int = Field(1950, ge=1950, le=2100)
    end_year: int = Field(2100, ge=1950, le=2100)

    @field_validator("address")
    @classmethod
    def address_must_be_printable(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Address cannot be empty.")
        if any(ch not in string.printable for ch in v):
            raise ValueError("Address contains non-printable characters.")
        if "  " in v:
            v = " ".join(v.split())
        return v

    @field_validator("end_year")
    @classmethod
    def end_year_not_before_start(cls, v: int, info):
        start = info.data.get("start_year")
        if start is not None and v < start:
            raise ValueError("end_year must be greater than or equal to start_year")
        return v


class GeocodeInfo(BaseModel):
    lat: float
    lon: float
    provider: str
    match_type: Optional[str] = None


class TornadoResult(BaseModel):
    event_id: int
    distance_m: float
    distance_miles: float
    distance_km: float
    selected_unit: Literal["miles", "km"]
    selected_distance: float
    distance_type: Literal["centerline", "estimated_damage_path_edge"]
    tor_f_scale: Optional[str] = None
    begin_dt: Optional[str] = None
    end_dt: Optional[str] = None
    state: Optional[str] = None
    cz_name: Optional[str] = None
    wfo: Optional[str] = None
    tor_length_miles: Optional[float] = None
    tor_width_yards: Optional[int] = None
    track_geojson: Dict[str, Any]
    closest_point_geojson: Dict[str, Any]
    corridor_geojson: Optional[Dict[str, Any]] = None
    notes: List[str]
    data_source: Dict[str, str]


class ClosestTornadoResponse(BaseModel):
    query: GeocodeInfo
    result: TornadoResult
    top_results: List[TornadoResult]
    share_url: str
