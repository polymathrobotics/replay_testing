# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
import logging


def get_logger():
    logger = logging.getLogger("replay_testing")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
