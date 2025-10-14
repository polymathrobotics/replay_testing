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

import base64
import os
import subprocess
from pathlib import Path

from ..logging_config import get_logger
from ..models import Mcap
from .base_fixture import BaseFixture

_logger_ = get_logger()


class NexusFixture(BaseFixture):
    """Fixture provider that downloads MCAP files from Nexus repository."""

    NEXUS_CI_USERNAME = os.getenv('NEXUS_CI_USERNAME', '')
    NEXUS_CI_PASSWORD = os.getenv('NEXUS_CI_PASSWORD', '')
    NEXUS_SERVER = os.getenv('NEXUS_SERVER', '')
    NEXUS_REPOSITORY = os.getenv('NEXUS_REPOSITORY', 'rosbag-hosted')

    def __init__(self, path: str):
        self.nexus_path = path

    @property
    def fixture_key(self) -> str:
        return Path(self.nexus_path).stem

    def download(self, destination_folder: Path) -> Mcap:
        """Download fixtures from Nexus repository.

        Returns:
            Mcap: A Mcap object with paths
            to downloaded files
        """

        if self.NEXUS_CI_USERNAME == 'ci':
            decoded_password = base64.b64decode(self.NEXUS_CI_PASSWORD).decode().strip()
        else:
            decoded_password = self.NEXUS_CI_PASSWORD
        _logger_.info(f'NEXUS_SERVER: {self.NEXUS_SERVER}')
        _logger_.info(f'NEXUS_REPOSITORY: {self.NEXUS_REPOSITORY}')
        _logger_.info(f'Downloading {self.nexus_path} to {destination_folder}')

        server = self.NEXUS_SERVER
        repo = self.NEXUS_REPOSITORY
        username = self.NEXUS_CI_USERNAME

        nexus_filename = self.nexus_path.split('/')[-1]

        curl_dest = destination_folder / nexus_filename

        curl_command = [
            'curl',
            '-v',
            '-u',
            f'{username}:{decoded_password}',
            '-sL',
            '-o',
            str(curl_dest),
            f'{server}/repository/{repo}/{self.nexus_path}',
        ]

        result = subprocess.run(curl_command, capture_output=True, text=True)

        if result.returncode == 0:
            _logger_.info(f'Download successful: {curl_dest}')
            return Mcap(path=curl_dest)
        else:
            _logger_.error(f'Download failed for {self.nexus_path}')
            _logger_.error(f'STDOUT: {result.stdout}')
            _logger_.error(f'STDERR: {result.stderr}')
            raise RuntimeError(f'Failed to download fixture from Nexus: {self.nexus_path}')
