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

import abc
from pathlib import Path

from ..models import Mcap


class BaseFixture(abc.ABC):
    @property
    @abc.abstractmethod
    def fixture_key(self) -> str:
        """A unique key identifying this fixture.
        This property must be implemented by child classes to provide
        a unique identifier for the fixture.
        Returns:
            str: A unique key for the fixture.
        """
        pass

    @abc.abstractmethod
    def download(self, destination: Path) -> Mcap:
        """Download the fixture files and return a Mcap object.

        This method must be implemented by child classes to retrieve
        fixture files from the appropriate source.

        Returns:
            Mcap: A Mcap object with paths
            to the downloaded files
        """
        pass
