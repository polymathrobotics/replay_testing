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
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..logging_config import get_logger
from ..models import McapFixture
from .base_fixture import BaseFixture

_logger_ = get_logger()


class S3Fixture(BaseFixture):
    """Fixture provider that downloads MCAP files from AWS S3."""

    def __init__(
        self,
        key: str,
        bucket: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """Initialize S3Fixture.

        Args:
            key: S3 object key (path within bucket)
            bucket: S3 bucket name
            region_name: AWS region (defaults to environment or AWS config)
            aws_access_key_id: AWS access key (defaults to environment or AWS config)
            aws_secret_access_key: AWS secret key (defaults to environment or AWS config)
            aws_session_token: AWS session token for temporary credentials (optional)
            endpoint_url: Custom S3 endpoint URL (e.g., for MinIO or other S3-compatible storage)
        """
        self.key = key
        self.bucket = bucket or os.getenv('AWS_BUCKET', '')
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_session_token = aws_session_token or os.getenv('AWS_SESSION_TOKEN')
        self.endpoint_url = endpoint_url or os.getenv('AWS_S3_ENDPOINT_URL')

    def _create_s3_client(self):
        """Create and return an S3 client with the configured credentials."""
        session_kwargs = {}

        if self.aws_access_key_id and self.aws_secret_access_key:
            session_kwargs['aws_access_key_id'] = self.aws_access_key_id
            session_kwargs['aws_secret_access_key'] = self.aws_secret_access_key

            if self.aws_session_token:
                session_kwargs['aws_session_token'] = self.aws_session_token

        session = boto3.Session(**session_kwargs)

        client_kwargs = {'service_name': 's3'}
        if self.region_name:
            client_kwargs['region_name'] = self.region_name
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url

        return session.client(**client_kwargs)

    def download(self, destination_folder: str) -> McapFixture:
        """Download fixture from S3.

        Args:
            destination_folder: Local folder to download the file to

        Returns:
            McapFixture: A McapFixture object with path to the downloaded file

        Raises:
            RuntimeError: If download fails
        """
        # Extract filename from S3 key
        filename = os.path.basename(self.key)
        if not filename:
            raise TypeError(f'No valid path provided: {filename}')

        # Ensure destination folder exists
        Path(destination_folder).mkdir(parents=True, exist_ok=True)

        # Full path for downloaded file
        local_path = os.path.join(destination_folder, filename)

        _logger_.info(f'Downloading s3://{self.bucket}/{self.key} to {local_path}')
        if self.endpoint_url:
            _logger_.info(f'Using endpoint: {self.endpoint_url}')

        try:
            s3_client = self._create_s3_client()

            # Check if object exists and get metadata
            try:
                response = s3_client.head_object(Bucket=self.bucket, Key=self.key)
                file_size = response.get('ContentLength', 0)
                _logger_.info(f'File size: {file_size / (1024 * 1024):.2f} MB')
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    raise RuntimeError(f'S3 object not found: s3://{self.bucket}/{self.key}')
                else:
                    raise RuntimeError(f'Failed to get object metadata: {str(e)}')

            # Download the file
            s3_client.download_file(
                Bucket=self.bucket,
                Key=self.key,
                Filename=local_path,
            )

            _logger_.info(f'Download successful: {local_path}')

            # Verify the downloaded file exists
            if not os.path.exists(local_path):
                raise RuntimeError(f'Downloaded file not found at {local_path}')

            # Verify it's an MCAP file
            if not local_path.endswith('.mcap'):
                _logger_.warning(f'Downloaded file does not have .mcap extension: {local_path}')

            return McapFixture(path=local_path)

        except NoCredentialsError:
            _logger_.error('AWS credentials not found. Please configure AWS credentials.')
            raise RuntimeError(
                'AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or configure AWS CLI.'
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            _logger_.error(f'S3 download failed with error {error_code}: {error_message}')
            raise RuntimeError(f'Failed to download from S3: {error_message}')
        except Exception as e:
            _logger_.error(f'Unexpected error during S3 download: {str(e)}')
            raise RuntimeError(f'Failed to download fixture from S3: {str(e)}')

    def __repr__(self):
        """String representation of S3Fixture."""
        return f'S3Fixture(bucket={self.bucket}, key={self.key})'
