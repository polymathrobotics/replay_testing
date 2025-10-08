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
        s3_client: Optional[boto3.client] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """Initialize S3Fixture.

        Args:
            key: S3 object key (path within bucket)
            bucket: S3 bucket name (can be set via AWS_BUCKET env var if not provided)
            s3_client: Pre-configured boto3 S3 client. If provided, takes priority over other auth methods.
            region_name: AWS region (defaults to environment or AWS config)
            aws_access_key_id: AWS access key (conflicts with environment variables if both are set)
            aws_secret_access_key: AWS secret key (conflicts with environment variables if both are set)
            aws_session_token: AWS session token for temporary credentials (optional)
            endpoint_url: Custom S3 endpoint URL (e.g., for MinIO or other S3-compatible storage)

        Raises:
            ValueError: If both explicit credentials and environment variables are provided

        Notes:
            Authentication priority:
            1. If s3_client is provided, it will be used directly
            2. If credential parameters are provided, they will be used to create a client
            3. If neither are provided, boto3 default credential chain is used (env vars, ~/.aws/credentials, etc.)
        """
        self.key = key
        self.bucket = bucket or os.getenv('AWS_BUCKET', '')
        self.s3_client = s3_client

        # Validate bucket name early
        if not self.bucket:
            raise ValueError(
                'S3 bucket name is required. Please provide it via the "bucket" parameter '
                'or set the AWS_BUCKET environment variable.'
            )

        if not self.s3_client:
            # Check for ambiguous credential configuration
            has_explicit_creds = aws_access_key_id or aws_secret_access_key
            has_env_creds = os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('AWS_SECRET_ACCESS_KEY')

            if has_explicit_creds and has_env_creds:
                # Only raise if the explicit creds differ from env creds
                if (aws_access_key_id and aws_access_key_id != os.getenv('AWS_ACCESS_KEY_ID')) or (
                    aws_secret_access_key and aws_secret_access_key != os.getenv('AWS_SECRET_ACCESS_KEY')
                ):
                    raise ValueError(
                        'Ambiguous credentials: both explicit parameters and environment variables are set. '
                        'Please use only one method or pass a pre-configured s3_client.'
                    )

            self.session_kwargs = {}
            self.session_kwargs['aws_access_key_id'] = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
            self.session_kwargs['aws_secret_access_key'] = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            if aws_session_token or os.getenv('AWS_SESSION_TOKEN'):
                self.session_kwargs['aws_session_token'] = aws_session_token or os.getenv('AWS_SESSION_TOKEN')

            self.client_kwargs: dict[str, str | None] = {}
            self.client_kwargs['service_name'] = 's3'
            self.client_kwargs['region_name'] = region_name or os.getenv('AWS_DEFAULT_REGION')
            self.client_kwargs['endpoint_url'] = endpoint_url or os.getenv('AWS_S3_ENDPOINT_URL')

    def _get_s3_client(self):
        """Get the S3 client, either the provided one or create a new one.

        Returns:
            boto3.client: S3 client instance
        """
        # If a client was provided, use it directly
        if self.s3_client:
            return self.s3_client

        # Create session with explicit credentials or let boto3 use its default chain
        session = boto3.Session(**self.session_kwargs) if self.session_kwargs else boto3.Session()
        return session.client(**self.client_kwargs)

    def download(self, destination_folder: Path) -> McapFixture:
        """Download fixture from S3.

        Args:
            destination_folder: Local folder to download the file to

        Returns:
            McapFixture: A McapFixture object with path to the downloaded file

        Raises:
            RuntimeError: If download fails
        """
        # Extract filename from S3 key
        filename = Path(self.key).name
        if not filename:
            raise TypeError(f'No valid path provided: {filename}')

        # Ensure destination folder exists
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Full path for downloaded file
        local_path = destination_folder / filename

        _logger_.info(f'Downloading s3://{self.bucket}/{self.key} to {local_path}')

        try:
            s3_client = self._get_s3_client()

            # Check if object exists and get metadata
            try:
                response = s3_client.head_object(Bucket=self.bucket, Key=self.key)
                file_size = response.get('ContentLength', 0)
                _logger_.info(f'File size: {file_size / (1024 * 1024):.4f} MB')
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
            if not local_path.exists():
                raise RuntimeError(f'Downloaded file not found at {local_path}')

            # Verify it's an MCAP file
            if not local_path.suffix == '.mcap':
                _logger_.warning(f'Downloaded file does not have .mcap extension: {local_path}')

            return McapFixture(path=local_path)

        except NoCredentialsError as e:
            _logger_.error('AWS credentials not found.')
            raise RuntimeError(
                'AWS credentials not found. Please provide credentials using one of the following methods:\n'
                '  1. Pass a pre-configured s3_client to S3Fixture\n'
                '  2. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables\n'
                '  3. Configure AWS CLI with "aws configure"\n'
                '  4. Create ~/.aws/credentials file\n'
                '  5. Use IAM roles (if running on AWS infrastructure)\n'
                f'Original error: {str(e)}'
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            _logger_.error(f'S3 download failed with error {error_code}: {error_message}')

            # Provide more helpful error messages for common issues
            if error_code == 'AccessDenied':
                raise RuntimeError(
                    f'Access denied to s3://{self.bucket}/{self.key}\n'
                    'Please check that:\n'
                    '  1. Your AWS credentials have permission to access this bucket/object\n'
                    '  2. The bucket and key are correct\n'
                    '  3. If using a custom endpoint, verify it is configured correctly\n'
                    f'Original error: {error_message}'
                )
            elif error_code == 'NoSuchBucket':
                raise RuntimeError(
                    f'S3 bucket "{self.bucket}" does not exist.\nPlease verify the bucket name is correct.'
                )
            elif error_code == 'InvalidAccessKeyId':
                raise RuntimeError('Invalid AWS Access Key ID.\nPlease verify your AWS credentials are correct.')
            elif error_code == 'SignatureDoesNotMatch':
                raise RuntimeError(
                    'AWS signature does not match. This usually means the Secret Access Key is incorrect.\n'
                    'Please verify your AWS credentials.'
                )
            else:
                raise RuntimeError(f'Failed to download from S3: {error_message}')
        except Exception as e:
            _logger_.error(f'Unexpected error during S3 download: {str(e)}')
            raise RuntimeError(f'Failed to download fixture from S3: {str(e)}')

    def __repr__(self):
        """String representation of S3Fixture."""
        return f'S3Fixture(bucket={self.bucket}, key={self.key})'
