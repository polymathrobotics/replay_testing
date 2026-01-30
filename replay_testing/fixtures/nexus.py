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

import os
import subprocess
from pathlib import Path

from ..logging_config import get_logger
from ..models import Mcap
from .base_fixture import BaseFixture

_logger_ = get_logger()


class NexusFixture(BaseFixture):
    """Fixture provider that downloads MCAP files from Nexus repository."""

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
        # Read environment variables at runtime, not at class definition time
        username = os.getenv('NEXUS_USERNAME', '')
        password = os.getenv('NEXUS_PASSWORD', '')
        server = os.getenv('NEXUS_SERVER', '')
        repo = os.getenv('NEXUS_REPOSITORY', '')
        extra_headers = os.getenv('NEXUS_EXTRA_HEADERS', '')
        _logger_.info(f'NEXUS_SERVER: {server}')
        _logger_.info(f'NEXUS_REPOSITORY: {repo}')
        _logger_.info(f'NEXUS_USERNAME: {username}')
        _logger_.info(f'Downloading {self.nexus_path} to {destination_folder}')

        nexus_filename = self.nexus_path.split('/')[-1]

        curl_dest = destination_folder / nexus_filename

        curl_command = [
            'curl',
            '-v',
            '-u',
            f'{username}:{password}',
            '-sL',
            '-o',
            str(curl_dest),
            '-w',
            '%{http_code}',
            f'{server}/repository/{repo}/{self.nexus_path}',
        ]

        if extra_headers:
            for header in extra_headers.split(';'):
                header = header.strip()
                if header:
                    curl_command.extend(['-H', header])

        result = subprocess.run(curl_command, capture_output=True, text=True)

        http_code = result.stdout.strip()

        if result.returncode != 0:
            _logger_.error(f'Download failed for {self.nexus_path}')
            _logger_.error(f'HTTP status code: {http_code}')
            _logger_.error(f'STDERR: {result.stderr}')
            raise RuntimeError(f'Failed to download fixture from Nexus: {self.nexus_path}')

        if not http_code.startswith('2'):
            _logger_.error(f'Download failed for {self.nexus_path}')
            _logger_.error(f'HTTP status code: {http_code}')
            _logger_.error(f'STDERR: {result.stderr}')
            raise RuntimeError(f'Failed to download fixture from Nexus: {self.nexus_path} (HTTP {http_code})')

        # Verify the downloaded file is an MCAP by checking magic bytes
        mcap_magic = b'\x89MCAP0\r\n'
        with Path.open(curl_dest, 'rb') as f:
            file_header = f.read(len(mcap_magic))
        if file_header != mcap_magic:
            _logger_.error(f'Downloaded file is not a valid MCAP: {curl_dest}')
            _logger_.error(f'Expected magic bytes: {mcap_magic!r}, got: {file_header!r}')
            raise RuntimeError(
                f'Downloaded file is not a valid MCAP (possibly a Cloudflare challenge page): {self.nexus_path}'
            )

        _logger_.info(f'Download successful: {curl_dest} (HTTP {http_code})')
        return Mcap(path=curl_dest)
