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

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import requests

from ..logging_config import get_logger
from ..models import Mcap
from .base_fixture import BaseFixture

_logger_ = get_logger()

CACHE_DIR = Path('/tmp/replay_testing/.cache')


class NexusFixture(BaseFixture):
    """Fixture provider that downloads MCAP files from Nexus repository."""

    def __init__(self, path: str):
        self.nexus_path = path

    @property
    def fixture_key(self) -> str:
        return Path(self.nexus_path).stem

    def _get_asset_metadata(
        self, server: str, repo: str, username: str, password: str, extra_headers: str
    ) -> Optional[dict]:
        """Fetch asset metadata from Nexus REST API.

        Returns:
            dict: Asset metadata containing 'id' and 'checksum', or None if not found
        """
        search_url = f'{server}/service/rest/v1/search/assets'
        # Nexus API expects paths with a leading forward-slash
        search_path = self.nexus_path if self.nexus_path.startswith('/') else f'/{self.nexus_path}'
        params = {
            'repository': repo,
            'name': search_path,
        }

        _logger_.info(f'Fetching asset metadata from Nexus API for path: {self.nexus_path}')

        headers = {}
        if extra_headers:
            for header in extra_headers.split(';'):
                header = header.strip()
                if header and ':' in header:
                    key, value = header.split(':', 1)
                    headers[key.strip()] = value.strip()

        try:
            response = requests.get(
                search_url,
                params=params,
                auth=(username, password),
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            items = data.get('items', [])
            if not items:
                _logger_.warning(f'No asset found for path: {self.nexus_path}')
                return None

            # Find exact match for our path
            for item in items:
                item_path = item.get('path', '')
                if item_path == self.nexus_path or item_path == f'/{self.nexus_path}':
                    asset_id = item.get('id')
                    checksum = item.get('checksum', {})
                    # Prefer sha256, fall back to sha1 or md5
                    checksum_value = checksum.get('sha256') or checksum.get('sha1') or checksum.get('md5')
                    checksum_type = 'sha256' if checksum.get('sha256') else 'sha1' if checksum.get('sha1') else 'md5'

                    if checksum_value:
                        return {
                            'id': asset_id,
                            'checksum': f'{checksum_type}:{checksum_value}',
                        }
                    else:
                        return {'id': asset_id, 'checksum': None}

            _logger_.warning(f'No exact match found for path: {self.nexus_path}')
            return None

        except requests.RequestException as e:
            _logger_.warning(f'Failed to fetch asset metadata from Nexus API: {e}')
            return None

    def _get_cache_paths(self, repo: str) -> tuple[Path, Path]:
        """Get cache file and metadata paths.

        Returns:
            tuple: (cache_file_path, metadata_file_path)
        """
        cache_key = f'{repo}/{self.nexus_path}'
        cache_path = CACHE_DIR / cache_key
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = cache_path.parent / f'{cache_path.name}.meta'
        return cache_path, metadata_path

    def _is_cache_valid(self, cache_path: Path, metadata_path: Path, expected_metadata: Optional[dict]) -> bool:
        """Check if cached file is valid by comparing checksums and IDs.

        Returns:
            bool: True if cache is valid, False otherwise
        """
        if not cache_path.exists():
            return False

        if not expected_metadata:
            _logger_.warning('No metadata available from Nexus, invalidating cache')
            return False

        expected_checksum = expected_metadata.get('checksum')
        expected_id = expected_metadata.get('id')

        if not expected_checksum:
            _logger_.warning('No checksum available, invalidating cache')
            return False

        if not metadata_path.exists():
            _logger_.info('Metadata file missing, cache invalid')
            return False

        try:
            with metadata_path.open('r') as f:
                metadata = json.load(f)
                cached_checksum = metadata.get('checksum')
                cached_id = metadata.get('id')

                # Check both checksum and ID for validation
                if cached_checksum == expected_checksum:
                    if expected_id and cached_id and cached_id != expected_id:
                        _logger_.info('Asset ID changed, cache invalid')
                        return False
                    _logger_.info(f'Cache hit: {cache_path}')
                    return True
                else:
                    _logger_.info('Checksum mismatch, cache invalid')
                    return False
        except (json.JSONDecodeError, IOError) as e:
            _logger_.warning(f'Failed to read metadata: {e}')
            return False

    def _write_metadata(self, metadata_path: Path, repo: str, asset_metadata: Optional[dict]):
        """Write metadata file with checksum and ID information."""
        metadata = {
            'repository': repo,
            'path': self.nexus_path,
            'id': asset_metadata.get('id') if asset_metadata else None,
            'checksum': asset_metadata.get('checksum') if asset_metadata else None,
        }
        try:
            with metadata_path.open('w') as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            _logger_.warning(f'Failed to write metadata: {e}')

    def _verify_mcap(self, file_path: Path) -> bool:
        """Verify the file is a valid MCAP by checking magic bytes."""
        mcap_magic = b'\x89MCAP0\r\n'
        with Path.open(file_path, 'rb') as f:
            file_header = f.read(len(mcap_magic))
        return file_header == mcap_magic

    def _download_to_path(
        self, dest_path: Path, server: str, repo: str, username: str, password: str, extra_headers: str
    ) -> tuple[bool, str]:
        """Download the file from Nexus to the specified path.

        Returns:
            tuple: (success, http_code)
        """
        curl_command = [
            'curl',
            '-v',
            '-u',
            f'{username}:{password}',
            '-sL',
            '-o',
            str(dest_path),
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
            return False, http_code

        if not http_code.startswith('2'):
            _logger_.error(f'Download failed for {self.nexus_path}')
            _logger_.error(f'HTTP status code: {http_code}')
            _logger_.error(f'STDERR: {result.stderr}')
            return False, http_code

        return True, http_code

    def download(self, destination_folder: Path) -> Mcap:
        """Download fixtures from Nexus repository with caching support.

        Returns:
            Mcap: A Mcap object with paths to downloaded files
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
        local_path = destination_folder / nexus_filename

        # Ensure destination folder exists
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Get asset metadata from Nexus API for cache validation
        asset_metadata = self._get_asset_metadata(server, repo, username, password, extra_headers)

        # Get cache paths
        cache_path, metadata_path = self._get_cache_paths(repo)

        # Check if we have a valid cached version
        if self._is_cache_valid(cache_path, metadata_path, asset_metadata):
            _logger_.info(f'Using cached file from {cache_path}')
            shutil.copy2(cache_path, local_path)
            _logger_.info(f'Copied from cache to {local_path}')
            return Mcap(path=local_path)

        # Cache miss - need to download
        _logger_.info(f'Cache miss, downloading from Nexus: {self.nexus_path}')

        # Download to cache first
        _logger_.info(f'Downloading to cache: {cache_path}')
        success, http_code = self._download_to_path(cache_path, server, repo, username, password, extra_headers)

        if not success:
            raise RuntimeError(f'Failed to download fixture from Nexus: {self.nexus_path} (HTTP {http_code})')

        # Verify the downloaded file is an MCAP by checking magic bytes
        if not self._verify_mcap(cache_path):
            _logger_.error(f'Downloaded file is not a valid MCAP: {cache_path}')
            # Clean up invalid cache file
            cache_path.unlink(missing_ok=True)
            raise RuntimeError(
                f'Downloaded file is not a valid MCAP (possibly a Cloudflare challenge page): {self.nexus_path}'
            )

        # Write metadata for future cache validation
        self._write_metadata(metadata_path, repo, asset_metadata)

        # Copy from cache to destination
        shutil.copy2(cache_path, local_path)

        _logger_.info(f'Download successful: {local_path} (HTTP {http_code})')
        return Mcap(path=local_path)
