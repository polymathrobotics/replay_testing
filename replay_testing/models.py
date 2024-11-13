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
