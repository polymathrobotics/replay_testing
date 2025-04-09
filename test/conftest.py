# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
# conftest.py
import logging
import pytest


@pytest.fixture(autouse=True)
def configure_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
