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

import pathlib

import mcap_ros2.reader
from launch import LaunchDescription
from launch.actions import ExecuteProcess

from replay_testing import (
    McapFixture,
    analyze,
    fixtures,
    run,
)

cmd_vel_only_fixture = (pathlib.Path(__file__).parent.parent / 'fixtures' / 'cmd_vel_only.mcap').as_posix()


@fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
class FilterFixtures:
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
    def test_expected_failure(self):
        msgs_it = mcap_ros2.reader.read_ros2_messages(self.reader, topics=['/user/cmd_vel'])

        msgs = [msg for msg in msgs_it]
        assert len(msgs) == 1
        assert msgs[0].channel.topic == '/nonexistent/cmd_vel'
