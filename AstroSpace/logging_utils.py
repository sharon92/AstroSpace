import logging
import os
import sys

from flask import current_app, has_app_context


DEBUG_FLAG = "--debug"
TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSY_VALUES = {"0", "false", "no", "off"}
FALLBACK_LOGGER_NAME = "AstroSpace.runtime"
FALLBACK_LOG_FORMAT = "[AstroSpace %(levelname)s] %(message)s"


def _coerce_env_bool(value):
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in TRUTHY_VALUES:
        return True
    if normalized in FALSY_VALUES:
        return False
    return None


def runtime_debug_enabled(argv=None, environ=None):
    env = os.environ if environ is None else environ
    env_enabled = _coerce_env_bool(env.get("ASTROSPACE_DEBUG"))
    if env_enabled is not None:
        return env_enabled

    args = sys.argv[1:] if argv is None else argv
    return DEBUG_FLAG in args


def strip_debug_flag(args):
    filtered_args = []
    debug_enabled = False

    for arg in args:
        if arg == DEBUG_FLAG:
            debug_enabled = True
            continue
        filtered_args.append(arg)

    return filtered_args, debug_enabled


def _fallback_logger():
    logger = logging.getLogger(FALLBACK_LOGGER_NAME)
    if getattr(logger, "_astrospace_configured", False):
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(FALLBACK_LOG_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger._astrospace_configured = True
    return logger


def configure_app_logging(app):
    configured_value = app.config.get("ASTROSPACE_DEBUG")
    if configured_value is None:
        configured_value = runtime_debug_enabled()

    app.config["ASTROSPACE_DEBUG"] = bool(configured_value)

    if app.config["ASTROSPACE_DEBUG"]:
        app.logger.setLevel(logging.DEBUG)
        debug_log(
            "Debug logging enabled (pid=%s, testing=%s, db_host=%s, db_name=%s, upload_path=%s)",
            os.getpid(),
            app.config.get("TESTING", False),
            app.config.get("DB_HOST"),
            app.config.get("DB_NAME"),
            app.config.get("UPLOAD_PATH"),
            level=logging.INFO,
        )

    return app.config["ASTROSPACE_DEBUG"]


def debug_log(message, *args, level=logging.DEBUG, **kwargs):
    if has_app_context():
        if not current_app.config.get("ASTROSPACE_DEBUG", False):
            return
        current_app.logger.log(level, message, *args, **kwargs)
        return

    if runtime_debug_enabled():
        _fallback_logger().log(level, message, *args, **kwargs)
