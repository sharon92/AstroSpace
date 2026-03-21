import logging
import os
import sys

from AstroSpace.logging_utils import debug_log, runtime_debug_enabled, strip_debug_flag


DEFAULT_GUNICORN_OPTIONS = [
    "-w",
    "3",
    "-b",
    "0.0.0.0:9000",
    "--timeout",
    "1000",
    "--worker-class",
    "gevent",
]
APP_TARGET = "AstroSpace:create_app()"


def build_gunicorn_command(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    filtered_args, flag_requested = strip_debug_flag(args)
    debug_enabled = flag_requested or runtime_debug_enabled(filtered_args)

    command = ["gunicorn", *DEFAULT_GUNICORN_OPTIONS]
    if debug_enabled:
        command.extend(["--log-level", "debug"])
    command.extend(filtered_args)
    command.append(APP_TARGET)
    return command, debug_enabled


def main(argv=None):
    command, debug_enabled = build_gunicorn_command(argv)
    if debug_enabled:
        os.environ["ASTROSPACE_DEBUG"] = "1"
        debug_log("Starting Gunicorn with AstroSpace debug logging enabled.", level=logging.INFO)

    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
