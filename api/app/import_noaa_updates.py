import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from .import_noaa_year import ensure_downloaded_filename, import_year, latest_details_files_by_year

engine = create_engine(os.environ["DATABASE_URL"])

UPSERT_YEAR_SQL = text(
    """
    INSERT INTO noaa_details_version (year, filename, revision, attempted_rows, inserted_rows, imported_at)
    VALUES (:year, :filename, :revision, :attempted_rows, :inserted_rows, NOW())
    ON CONFLICT (year)
    DO UPDATE SET
      filename = EXCLUDED.filename,
      revision = EXCLUDED.revision,
      attempted_rows = EXCLUDED.attempted_rows,
      inserted_rows = EXCLUDED.inserted_rows,
      imported_at = NOW();
    """
)


CLEANUP_FUTURE_DATES_SQL = text(
    """
    UPDATE tornado_event
    SET begin_dt = CASE
            WHEN begin_dt IS NOT NULL
                 AND EXTRACT(YEAR FROM begin_dt) > :max_expected_year
                 AND EXTRACT(YEAR FROM begin_dt) <= :max_shiftable_year
            THEN begin_dt - INTERVAL '100 years'
            ELSE begin_dt
        END,
        end_dt = CASE
            WHEN end_dt IS NOT NULL
                 AND EXTRACT(YEAR FROM end_dt) > :max_expected_year
                 AND EXTRACT(YEAR FROM end_dt) <= :max_shiftable_year
            THEN end_dt - INTERVAL '100 years'
            ELSE end_dt
        END
    WHERE (begin_dt IS NOT NULL
           AND EXTRACT(YEAR FROM begin_dt) > :max_expected_year
           AND EXTRACT(YEAR FROM begin_dt) <= :max_shiftable_year)
       OR (end_dt IS NOT NULL
           AND EXTRACT(YEAR FROM end_dt) > :max_expected_year
           AND EXTRACT(YEAR FROM end_dt) <= :max_shiftable_year);
    """
)

UPDATE_META_SQL = text(
    """
    UPDATE dataset_refresh_meta
    SET data_last_refreshed = :data_last_refreshed,
        dataset_version = :dataset_version,
        updated_at = NOW()
    WHERE id = 1;
    """
)


def _existing_versions() -> dict[int, str]:
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT year, revision FROM noaa_details_version")).mappings().all()
    return {int(row["year"]): str(row["revision"]) for row in rows}



def cleanup_future_dates() -> int:
    current_year = datetime.now(timezone.utc).year
    with engine.begin() as conn:
        result = conn.execute(
            CLEANUP_FUTURE_DATES_SQL,
            {
                "max_expected_year": current_year + 1,
                "max_shiftable_year": current_year + 100,
            },
        )
    return int(result.rowcount or 0)


def refresh_updates(start_year: int = 1950) -> list[dict[str, int | str]]:
    latest = latest_details_files_by_year(start_year=start_year)
    current = _existing_versions()

    changed_years = []
    for year, info in latest.items():
        if current.get(year) != info["revision"]:
            changed_years.append((year, info["filename"], info["revision"]))

    changed_years.sort(key=lambda item: item[0])

    import_log: list[dict[str, int | str]] = []
    for year, filename, revision in changed_years:
        csv_path = ensure_downloaded_filename(filename)
        attempted, inserted = import_year(csv_path)

        with engine.begin() as conn:
            conn.execute(
                UPSERT_YEAR_SQL,
                {
                    "year": year,
                    "filename": filename,
                    "revision": revision,
                    "attempted_rows": attempted,
                    "inserted_rows": inserted,
                },
            )

        import_log.append(
            {
                "year": year,
                "revision": revision,
                "attempted_rows": attempted,
                "inserted_rows": inserted,
                "filename": filename,
            }
        )

    dataset_version = max((info["revision"] for info in latest.values()), default=None)
    with engine.begin() as conn:
        conn.execute(
            UPDATE_META_SQL,
            {
                "data_last_refreshed": datetime.now(timezone.utc).isoformat(),
                "dataset_version": dataset_version,
            },
        )

    corrected_rows = cleanup_future_dates()
    if corrected_rows:
        import_log.append({"year": "cleanup", "revision": "date-fix", "attempted_rows": corrected_rows, "inserted_rows": corrected_rows, "filename": "tornado_event"})

    return import_log


def main() -> None:
    import_log = refresh_updates(start_year=1950)
    if not import_log:
        print("No NOAA year revisions changed. Dataset metadata refreshed.")
        return

    print("Imported NOAA updates:")
    for item in import_log:
        print(
            f"year={item['year']} revision={item['revision']} "
            f"attempted={item['attempted_rows']} inserted={item['inserted_rows']}"
        )


if __name__ == "__main__":
    main()
