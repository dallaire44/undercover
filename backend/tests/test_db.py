from backend import db


def test_sqlite_without_database_url(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    assert db.engine().dialect.name == "sqlite"


def test_postgres_with_database_url(monkeypatch):
    made = {}

    def create_engine(address, **kwargs):
        made.update(kwargs, url=address)

    monkeypatch.setattr(db, "create_engine", create_engine)
    url = "postgresql://postgres.ref:secret@pooler.supabase.com:5432/postgres"
    monkeypatch.setenv("DATABASE_URL", url)
    db.engine_for.cache_clear()
    db.engine()
    assert made["url"].drivername == "postgresql+psycopg"
    assert (made["pool_size"], made["max_overflow"]) == (4, 0)
    assert made["connect_args"] == {"options": "-c search_path=undercover"}
    db.engine_for.cache_clear()
