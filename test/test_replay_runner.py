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
import types
from pathlib import Path

import pytest
from launch import LaunchDescription
from launch.actions import ExecuteProcess

from replay_testing import (
    LocalFixture,
    ReplayRunParams,
    ReplayTestingRunner,
    analyze,
    fixtures,
    get_sequential_mcap_reader,
    read_messages,
    run,
)

fixtures_dir = Path(__file__).parent / 'fixtures'

cmd_vel_only_fixture = fixtures_dir / 'cmd_vel_only.mcap'
cmd_vel_only_2_fixture = fixtures_dir / 'cmd_vel_only_2.mcap'

pub_cmd_vel = [
    'ros2',
    'topic',
    'pub',
    '--use-sim-time',
    '-r',
    '10',
    '/user/cmd_vel',
    'geometry_msgs/msg/Twist',
    '{linear: {x: 1.0}, angular: {z: 0.5}}',
]


def test_fixtures():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = []

    test_module.Fixtures = Fixtures
    runner = ReplayTestingRunner(test_module)
    replay_fixtures = runner.filter_fixtures()

    # Assert
    assert len(replay_fixtures) == 1

    filtered_fixture_path = replay_fixtures[0].filtered_fixture.path
    reader = get_sequential_mcap_reader(filtered_fixture_path)
    topics = reader.get_all_topics_and_types()

    assert len(topics) == 1
    assert topics[0].name == '/vehicle/cmd_vel'
    return


def test_fixtures_raises_err():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel', '/does_not_exist']
        expected_output_topics = []

    test_module.Fixtures = Fixtures
    runner = ReplayTestingRunner(test_module)

    with pytest.raises(AssertionError):
        runner.filter_fixtures()


def test_run():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = ['/user/cmd_vel']

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription([
                ExecuteProcess(
                    cmd=pub_cmd_vel,
                    name='topic_pub',
                    output='screen',
                )
            ])

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    runner = ReplayTestingRunner(test_module)

    runner.filter_fixtures()
    replay_fixtures = runner.run()

    # Assert
    assert len(replay_fixtures) == 1
    run_fixture = replay_fixtures[0].run_fixtures[0]
    reader = get_sequential_mcap_reader(run_fixture.path)
    topics = reader.get_all_topics_and_types()
    topic_names = [topic.name for topic in topics]

    assert '/vehicle/cmd_vel' in topic_names
    assert '/user/cmd_vel' in topic_names

    msg_reader = get_sequential_mcap_reader(run_fixture.path)
    msgs_it = read_messages(msg_reader, topics=['/user/cmd_vel'])

    msgs = [(topic_name, msg, timestamp) for topic_name, msg, timestamp in msgs_it]
    assert len(msgs) >= 1
    assert msgs[0][0] == '/user/cmd_vel'
    return


def test_analyze():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = ['/user/cmd_vel']

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription([
                ExecuteProcess(
                    cmd=pub_cmd_vel,
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

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.filter_fixtures()
    runner.run()
    exit_code, _ = runner.analyze()
    assert exit_code == 0

    return


def test_failed_analyze():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = ['/user/cmd_vel']

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription([
                ExecuteProcess(
                    cmd=pub_cmd_vel,
                    name='topic_pub',
                    output='screen',
                )
            ])

    @analyze
    class Analyze:
        def test_cmd_vel(self):
            self.assertEqual(False, True)

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.filter_fixtures()
    runner.run()
    exit_code, _ = runner.analyze(write_junit=False)
    assert exit_code == 1

    return


def test_multiple_fixtures():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([
        LocalFixture(path=cmd_vel_only_fixture),
        LocalFixture(path=cmd_vel_only_2_fixture),
    ])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = ['/user/cmd_vel']

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription([
                ExecuteProcess(
                    cmd=pub_cmd_vel,
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

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    replay_fixtures = runner.filter_fixtures()
    assert len(replay_fixtures) == 2
    assert len(replay_fixtures[0].run_fixtures) == 0
    assert len(replay_fixtures[1].run_fixtures) == 0

    replay_fixtures = runner.run()
    assert len(replay_fixtures) == 2
    assert len(replay_fixtures[0].run_fixtures) == 1
    assert len(replay_fixtures[1].run_fixtures) == 1

    exit_code, _ = runner.analyze()
    assert exit_code == 0

    return


def test_against_duplicate_fixture_keys():
    """Test that duplicate fixture keys raise an error."""
    test_module = types.ModuleType('test_module')

    # Both fixtures have the same stem name (cmd_vel_only), so they will have duplicate keys
    @fixtures.parameterize([
        LocalFixture(path=cmd_vel_only_fixture),
        LocalFixture(path=cmd_vel_only_fixture),  # Duplicate key
    ])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = []

    test_module.Fixtures = Fixtures
    runner = ReplayTestingRunner(test_module)

    # Expect an error when trying to filter fixtures with duplicate keys
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        runner.filter_fixtures()

    # Verify the error message mentions duplicate keys
    assert 'duplicate' in str(exc_info.value).lower()


def test_parametric_sweep():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
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

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.filter_fixtures()
    replay_fixtures = runner.run()
    exit_code, _ = runner.analyze()
    assert exit_code == 0

    assert len(replay_fixtures) == 1
    assert len(replay_fixtures[0].run_fixtures) == 2
    return


def test_only_analyze():
    test_module = types.ModuleType('test_module')

    @fixtures.parameterize([LocalFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        required_input_topics = ['/vehicle/cmd_vel']
        expected_output_topics = ['/user/cmd_vel']

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription([
                ExecuteProcess(
                    cmd=pub_cmd_vel,
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

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.filter_fixtures()
    runner.run()
    exit_code, _ = runner.analyze()
    assert exit_code == 0

    # Second analyze
    @analyze
    class AnalyzeSecondCmdVel:
        def test_cmd_vel(self):
            # Expect failure
            assert False

    test_module.Analyze = AnalyzeSecondCmdVel
    second_runner = ReplayTestingRunner(test_module, run_id=runner.run_id)
    exit_code, _ = second_runner.analyze(write_junit=False)
    assert exit_code == 1

    return
