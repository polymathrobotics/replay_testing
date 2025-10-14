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
import shutil
from pathlib import Path

from ..models import Mcap
from .base_fixture import BaseFixture


class LocalFixture(BaseFixture):
    def __init__(self, path: Path):
        self.path = path

    @property
    def fixture_key(self) -> str:
        return Path(self.path).stem

    def download(self, destination: Path) -> Mcap:
        mcap_path = destination / self.path.name
        shutil.copy(self.path, mcap_path)
        return Mcap(path=str(mcap_path))
