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

import boto3
from launch import LaunchDescription
from launch.actions import ExecuteProcess

from replay_testing import S3Fixture, analyze, fixtures, read_messages, run

# This example uses the default credential chain (env vars, ~/.aws/credentials, IAM roles, etc.)
# s3_client = boto3.client('s3')

# Alternatively, you can create a client with specific configuration:
# s3_client = boto3.client(
# 's3',
# region_name='us-west-2',
# aws_access_key_id='YOUR_ACCESS_KEY',
# aws_secret_access_key='YOUR_SECRET_KEY',
# )

# Or for MinIO/other S3-compatible storage:
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('AWS_S3_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION'),
)


@fixtures.parameterize([S3Fixture(key='generic/cmd_vel_only.mcap', bucket='replay-testing-bags', s3_client=s3_client)])
class Fixtures:
    required_input_topics = ['/vehicle/cmd_vel']
    expected_output_topics = ['/user/cmd_vel']


@run.default()
class Run:
    def generate_launch_description(self) -> LaunchDescription:
        return LaunchDescription([
            ExecuteProcess(
                cmd=[
                    'ros2',
                    'topic',
                    'pub',
                    '--use-sim-time',
                    '-r',
                    '10',
                    '/user/cmd_vel',
                    'geometry_msgs/msg/Twist',
                    '{linear: {x: 1.0}, angular: {z: 0.5}}',
                ],
                name='topic_pub',
                output='screen',
            )
        ])


@analyze
class AnalyzeBasicReplay:
    def test_cmd_vel(self):
        msgs_it = read_messages(self.reader, topics=['/user/cmd_vel'])

        msgs = [(topic_name, msg, timestamp) for topic_name, msg, timestamp in msgs_it]
        assert len(msgs) >= 1
        assert msgs[0][0] == '/user/cmd_vel'
