# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from enum import Enum
from typing import Optional

from mcap_ros2.reader import McapReader
from pydantic import BaseModel


class ReplayTestingPhase(Enum):
    FIXTURES = 'fixtures'
    RUN = 'run'
    ANALYZE = 'analyze'


class RunnerArgs(BaseModel):
    use_clock: bool = True
    playback_rate: float = 1.0


class ReplayRunParams(BaseModel):
    name: str
    params: dict
    runner_args: RunnerArgs = RunnerArgs()


class Mcap(BaseModel):
    path: str
    reader: Optional[McapReader] = None

    class Config:
        arbitrary_types_allowed = True
