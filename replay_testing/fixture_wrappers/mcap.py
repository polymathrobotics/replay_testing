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

from ..models import Mcap
from .base_fixture import BaseFixture


class McapFixture(BaseFixture):
    def __init__(self, path: str):
        self.path = path

    def download(self, destination: str) -> Mcap:
        """Download the fixture files and return a Mcap object.

        This method must be implemented by child classes to retrieve
        fixture files from the appropriate source.

        Returns:
            Mcap: A Mcap object with paths
            to the downloaded files
        """
        mcap_path = f'{destination}/{self.path.split("/")[-1]}'
        shutil.copy(self.path, mcap_path)
        return Mcap(path=mcap_path)
