from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    census_benchmark: str = "Public_AR_Current"
    census_vintage: str = "Current_Current"

    # Nominatim fallback (OSM)
    nominatim_user_agent: str = "closest-tornado-dev (local)"
    nominatim_email: str | None = None  # optional, but recommended for identification
    admin_refresh_token: str | None = None

settings = Settings()