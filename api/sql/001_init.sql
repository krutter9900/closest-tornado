CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS tornado_event (
  event_id BIGINT PRIMARY KEY,
  begin_dt TIMESTAMP NULL,
  end_dt TIMESTAMP NULL,
  state TEXT NULL,
  cz_name TEXT NULL,
  wfo TEXT NULL,
  tor_f_scale TEXT NULL,
  tor_length_miles NUMERIC NULL,
  tor_width_yards INTEGER NULL,
  begin_lat DOUBLE PRECISION NULL,
  begin_lon DOUBLE PRECISION NULL,
  end_lat DOUBLE PRECISION NULL,
  end_lon DOUBLE PRECISION NULL,
  geom_line geometry(LineString, 4326) NULL,
  geog_line geography(LineString) NULL
);

CREATE INDEX IF NOT EXISTS tornado_event_geog_gist
  ON tornado_event
  USING GIST (geog_line);

CREATE INDEX IF NOT EXISTS tornado_event_begin_dt
  ON tornado_event (begin_dt);