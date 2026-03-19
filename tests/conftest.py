import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from AstroSpace import create_app

    monkeypatch.setattr("AstroSpace.blog.get_all_images", lambda *args, **kwargs: [])

    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DB_NAME": "test",
            "DB_USER": "test",
            "DB_PASSWORD": "test",
            "DB_HOST": "localhost",
            "DB_PORT": 5432,
            "TITLE": "AstroSpace Test",
            "UPLOAD_PATH": str(tmp_path / "uploads"),
            "SKIP_DB_INIT": True,
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()
