# -*- coding: utf-8 -*-
import os
import sys
from loguru import logger

script_path = os.path.split(os.path.realpath(sys.argv[0]))[0]
logger.add(
    f"{script_path}/logs/info.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
    serialize=False,
    enqueue=True,
    retention="7 days",
    rotation="500 KB",
)

logger.add(
    f"{script_path}/logs/error.log",
    level="ERROR",
    serialize=False,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
    enqueue=False,
    retention="7 days",
    rotation="200 KB",
)
