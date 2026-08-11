import logging
import os
from logging.handlers import RotatingFileHandler
from utils.paths import LOG_DIR


def setup_logger(log_dir=None):
    log_dir = os.fspath(LOG_DIR if log_dir is None else log_dir)
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger('battery_soh')
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fh = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'), encoding='utf-8',
        maxBytes=10 * 1024 * 1024, backupCount=5
    )
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
