import pytest
from pathlib import Path
from tempfile import gettempdir
from sqlalchemy import create_engine
from sqlalchemy.exc import ArgumentError

from app.config import Settings


def test_blank_database_url_uses_local_default(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "   ")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./delivery_agent.db"


def test_missing_database_url_uses_local_default(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./delivery_agent.db"


def test_blank_database_url_uses_vercel_temp_path(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "")
    settings = Settings(_env_file=None)
    expected = f"sqlite:///{Path(gettempdir(), 'delivery_agent.db').as_posix()}"
    assert settings.database_url == expected


def test_missing_database_url_uses_vercel_temp_path(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    expected = f"sqlite:///{Path(gettempdir(), 'delivery_agent.db').as_posix()}"
    assert settings.database_url == expected


def test_valid_sqlite_database_url_is_preserved(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./custom.db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./custom.db"


def test_invalid_non_empty_database_url_is_not_silently_replaced(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "invalid-database-url")
    settings = Settings(_env_file=None)
    with pytest.raises(ArgumentError):
        create_engine(settings.database_url)