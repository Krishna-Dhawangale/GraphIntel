from sqlalchemy.engine import make_url


def normalize_postgres_driver(database_url: str, driver: str) -> str:
    """Set an explicit SQLAlchemy driver for a generic PostgreSQL URL."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername=f"postgresql+{driver}").render_as_string(
            hide_password=False
        )
    return database_url
