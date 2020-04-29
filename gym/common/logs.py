import logging
import logging.config


logger = logging.getLogger(__name__)


class Logs:
    def __init__(self, filename, debug=False):
        """Starts logging for screen and file handlers
        By default INFO on screen and DEBUG in filename
        if debug specified, logs DEBUG on screen too

        Arguments:
            filename {string} -- Name of file (path included)
            where DEBUG logs must be written

        Keyword Arguments:
            debug {bool} -- If DEBUG must be shown on screen (default: {False})
        """

        op_mode = "DEBUG" if debug else "INFO"

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "strict": {
                        "format": "%(asctime)s [%(levelname)s] " "%(name)s: %(message)s"
                    },
                    "standard": {"format": "%(asctime)s [%(levelname)s]: %(message)s"},
                },
                "handlers": {
                    "default": {
                        "level": op_mode,
                        "class": "logging.StreamHandler",
                        "formatter": "standard",
                    },
                    "info_file_handler": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": "DEBUG",
                        "formatter": "strict",
                        "filename": filename,
                        "maxBytes": 10485760,
                        "backupCount": 20,
                        "encoding": "utf8",
                    },
                },
                "loggers": {
                    "": {
                        "handlers": ["default", "info_file_handler"],
                        "level": "DEBUG",
                        "propagate": True,
                    }
                },
            }
        )
        logger.info(f"Starting logs in {op_mode} mode")
        logger.info(f"Logging DEBUG mode into file {filename}")
