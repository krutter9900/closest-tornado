import time
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from .settings import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)

def wait_for_db(max_seconds: int = 60) -> None:
    """
    Postgres can take a few seconds to become ready even after the container is "Up".
    This retries until it's reachable or times out.
    """
    start = time.time()
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            if time.time() - start > max_seconds:
                raise
            time.sleep(2)

def run_migrations() -> None:
    wait_for_db()
    with engine.begin() as conn:
        sql = open("/app/sql/001_init.sql", "r", encoding="utf-8").read()
        conn.execute(text(sql))