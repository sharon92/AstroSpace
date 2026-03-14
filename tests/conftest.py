from datetime import datetime

import pytest


@pytest.fixture
def sample_blog():
    return {
        "id": 1,
        "title": "First Light",
        "slug": "first-light",
        "excerpt": "A short observing report.",
        "author": "astro",
        "image_path": "",
        "image_thumbnail": "",
        "content_html": "<p>Hello world</p>",
        "created_at": datetime(2025, 1, 1, 22, 0, 0),
    }


@pytest.fixture
def app(monkeypatch, tmp_path, sample_blog):
    from AstroSpace import create_app

    monkeypatch.setattr("AstroSpace.blog.get_all_images", lambda *args, **kwargs: [])
    monkeypatch.setattr("AstroSpace.blog.list_blogs", lambda *args, **kwargs: [sample_blog])
    monkeypatch.setattr("AstroSpace.blog_posts.list_blogs", lambda *args, **kwargs: [sample_blog])
    monkeypatch.setattr("AstroSpace.blog_posts.get_blog_by_slug", lambda slug: sample_blog if slug == sample_blog["slug"] else None)

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
