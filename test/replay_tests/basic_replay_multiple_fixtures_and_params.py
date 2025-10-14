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
from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess

from replay_testing import (
    LocalFixture,
    ReplayRunParams,
    analyze,
    fixtures,
    read_messages,
    run,
)

fixtures_dir = Path(__file__).parent.parent / 'fixtures'


@fixtures.parameterize([
    LocalFixture(path=fixtures_dir / 'cmd_vel_only.mcap'),
    LocalFixture(path=fixtures_dir / 'cmd_vel_only_2.mcap'),
])
class Fixtures:
    required_input_topics = ['/vehicle/cmd_vel']
    expected_output_topics = ['/user/cmd_vel']


@run.parameterize([
    ReplayRunParams(name='run_1_twist_slow', params={'x': 1.0}),
    ReplayRunParams(name='run_2_twist_fast', params={'x': 10.0}),
])
class Run:
    def generate_launch_description(self, replay_run_params: ReplayRunParams) -> LaunchDescription:
        print('replay_run_parms')
        twist_msg = {
            'linear': {'x': replay_run_params.params['x']},
            'angular': {'z': 0.5},
        }
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
                    json.dumps(twist_msg),
                ],
                name='topic_pub',
                output='screen',
            )
        ])


@analyze
class Analyze:
    def test_cmd_vel(self):
        msgs_it = read_messages(self.reader, topics=['/user/cmd_vel'])

        msgs = [(topic_name, msg, timestamp) for topic_name, msg, timestamp in msgs_it]
        assert len(msgs) >= 1
        assert msgs[0][0] == '/user/cmd_vel'
