__author__ = 'mehdi'
import logging
import logging.handlers

import sys
import syslog

logger = None

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL


def init_logger(server_log_format, server_logging_name, server_logging_file, max_logfile_size=1000000, nb_logfile=5):
    # initialize logging ...
    #logging.basicConfig(format=server_log_format, stream=sys.stdout, level=logging.DEBUG)
    logging.basicConfig(format=server_log_format,  level=logging.INFO, filename=server_logging_file)
    logger = logging.getLogger(server_logging_name)
    formatter = logging.Formatter(server_log_format)

    # create rotating file handler
    fh = logging.handlers.RotatingFileHandler(filename=server_logging_file, maxBytes=max_logfile_size, backupCount=nb_logfile)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler(strm=sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def log(message, level=INFO):
    """

    :param message:
    :param level:
    """
    if None != logger:
        logger.log(level, message)