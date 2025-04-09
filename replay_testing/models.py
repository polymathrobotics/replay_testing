# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
from pydantic import BaseModel
from typing import Optional

from mcap_ros2.reader import McapReader
from enum import Enum


class ReplayTestingPhase(Enum):
    FIXTURES = "fixtures"
    RUN = "run"
    ANALYZE = "analyze"


class ReplayRunParams(BaseModel):
    name: str
    params: dict


class McapFixture(BaseModel):
    path: str
    reader: Optional[McapReader] = None

    class Config:
        arbitrary_types_allowed = True
