import logging

from AstroSpace import create_app
from AstroSpace.__main__ import APP_TARGET, build_gunicorn_command
from AstroSpace.logging_utils import runtime_debug_enabled, strip_debug_flag


def test_runtime_debug_enabled_from_cli_flag(monkeypatch):
    monkeypatch.delenv("ASTROSPACE_DEBUG", raising=False)

    assert runtime_debug_enabled(["flask", "run", "--debug"]) is True


def test_runtime_debug_enabled_from_env(monkeypatch):
    monkeypatch.setenv("ASTROSPACE_DEBUG", "true")

    assert runtime_debug_enabled([]) is True


def test_strip_debug_flag_removes_only_debug_flag():
    filtered_args, debug_enabled = strip_debug_flag(["--workers", "1", "--debug", "--timeout", "30"])

    assert debug_enabled is True
    assert filtered_args == ["--workers", "1", "--timeout", "30"]


def test_build_gunicorn_command_enables_debug_log_level(monkeypatch):
    monkeypatch.delenv("ASTROSPACE_DEBUG", raising=False)

    command, debug_enabled = build_gunicorn_command(["--debug", "--workers", "1"])

    assert debug_enabled is True
    assert command[0] == "gunicorn"
    assert "--debug" not in command
    assert "--log-level" in command
    assert "debug" in command
    assert command[-1] == APP_TARGET
    assert command[command.index("--workers") + 1] == "1"


def test_create_app_honors_explicit_debug_config(tmp_path, monkeypatch):
    monkeypatch.delenv("ASTROSPACE_DEBUG", raising=False)

    app = create_app(
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
            "ASTROSPACE_DEBUG": True,
        }
    )

    assert app.config["ASTROSPACE_DEBUG"] is True
    assert app.logger.level == logging.DEBUG
