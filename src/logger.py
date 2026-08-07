import logging
from utils import find_project_root

# noinspection argument-list

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_format = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-15s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log_format = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-15s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler = logging.FileHandler(f"{find_project_root()}/data/logs/INFO.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_format)

file_handler2 = logging.FileHandler(f"{find_project_root()}/data/logs/DEBUG.log", encoding="utf-8")
file_handler2.setLevel(logging.DEBUG)
file_handler2.setFormatter(log_format)

file_handler3 = logging.FileHandler(f"{find_project_root()}/data/logs/ERROR.log", encoding="utf-8")
file_handler3.setLevel(logging.ERROR)
file_handler3.setFormatter(log_format)

logger.addHandler(file_handler)
logger.addHandler(file_handler2)
logger.addHandler(file_handler3)

logger.info("Logger initialized")
