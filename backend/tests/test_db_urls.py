import pytest

from app.db.urls import normalize_postgres_driver


@pytest.mark.parametrize(
    ("url", "driver", "expected"),
    [
        (
            "postgres://graphintel:password@db.example:5432/graphintel",
            "psycopg2",
            "postgresql+psycopg2://graphintel:password@db.example:5432/graphintel",
        ),
        (
            "postgresql://graphintel:password@db.example:5432/graphintel",
            "asyncpg",
            "postgresql+asyncpg://graphintel:password@db.example:5432/graphintel",
        ),
        (
            "postgresql+psycopg2://graphintel:password@db.example:5432/graphintel",
            "psycopg2",
            "postgresql+psycopg2://graphintel:password@db.example:5432/graphintel",
        ),
        ("sqlite:///./graphintel.db", "asyncpg", "sqlite:///./graphintel.db"),
    ],
)
def test_normalize_postgres_driver(url: str, driver: str, expected: str) -> None:
    assert normalize_postgres_driver(url, driver) == expected
