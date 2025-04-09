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

import types
import os
import pytest
from launch import LaunchDescription
from launch.actions import ExecuteProcess
import mcap_ros2.reader
import json
from ament_index_python.packages import get_package_share_directory

from replay_testing import (
    ReplayTestingRunner,
    fixtures,
    get_sequential_mcap_reader,
    run,
    get_message_mcap_reader,
    analyze,
    McapFixture,
    ReplayRunParams,
)


replay_testing_dir = get_package_share_directory("replay_testing")

cmd_vel_only_fixture = os.path.join(replay_testing_dir, "test", "fixtures", "cmd_vel_only.mcap")
cmd_vel_only_2_fixture = os.path.join(replay_testing_dir, "test", "fixtures", "cmd_vel_only_2.mcap")


def test_fixtures():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = []

    test_module.Fixtures = Fixtures
    runner = ReplayTestingRunner(test_module)
    replay_fixtures = runner.fixtures()

    # Assert
    assert len(replay_fixtures) == 1

    filtered_fixture_path = replay_fixtures[0].filtered_fixture.path
    reader = get_sequential_mcap_reader(filtered_fixture_path)
    topics = reader.get_all_topics_and_types()

    assert len(topics) == 1
    assert topics[0].name == "/vehicle/cmd_vel"
    return


def test_fixtures_raises_err():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel", "/does_not_exist"]
        output_topics = []

    test_module.Fixtures = Fixtures
    runner = ReplayTestingRunner(test_module)

    with pytest.raises(AssertionError):
        runner.fixtures()


def test_run():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = ["/user/cmd_vel"]

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription(
                [
                    ExecuteProcess(
                        cmd=[
                            "ros2",
                            "topic",
                            "pub",
                            "/user/cmd_vel",
                            "geometry_msgs/msg/Twist",
                            "{linear: {x: 1.0}, angular: {z: 0.5}}",
                        ],
                        name="topic_pub",
                        output="screen",
                    )
                ]
            )

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    runner = ReplayTestingRunner(test_module)

    runner.fixtures()
    replay_fixtures = runner.run()

    # Assert
    assert len(replay_fixtures) == 1
    run_fixture = replay_fixtures[0].run_fixtures[0]
    reader = get_sequential_mcap_reader(run_fixture.path)
    topics = reader.get_all_topics_and_types()
    topic_names = [topic.name for topic in topics]

    assert "/vehicle/cmd_vel" in topic_names
    assert "/user/cmd_vel" in topic_names

    msg_reader = get_message_mcap_reader(run_fixture.path)
    msgs_it = mcap_ros2.reader.read_ros2_messages(msg_reader, topics=["/user/cmd_vel"])

    msgs = [msg for msg in msgs_it]
    assert len(msgs) == 1
    assert msgs[0].channel.topic == "/user/cmd_vel"
    return


def test_analyze():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = ["/user/cmd_vel"]

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription(
                [
                    ExecuteProcess(
                        cmd=[
                            "ros2",
                            "topic",
                            "pub",
                            "/user/cmd_vel",
                            "geometry_msgs/msg/Twist",
                            "{linear: {x: 1.0}, angular: {z: 0.5}}",
                        ],
                        name="topic_pub",
                        output="screen",
                    )
                ]
            )

    @analyze
    class Analyze:
        def test_cmd_vel(self):
            msgs_it = mcap_ros2.reader.read_ros2_messages(self.reader, topics=["/user/cmd_vel"])

            msgs = [msg for msg in msgs_it]
            assert len(msgs) == 1
            assert msgs[0].channel.topic == "/user/cmd_vel"

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.fixtures()
    runner.run()
    exit_code, _ = runner.analyze()
    assert exit_code == 0

    return


def test_failed_analyze():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = ["/user/cmd_vel"]

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription(
                [
                    ExecuteProcess(
                        cmd=[
                            "ros2",
                            "topic",
                            "pub",
                            "/user/cmd_vel",
                            "geometry_msgs/msg/Twist",
                            "{linear: {x: 1.0}, angular: {z: 0.5}}",
                        ],
                        name="topic_pub",
                        output="screen",
                    )
                ]
            )

    @analyze
    class Analyze:
        def test_cmd_vel(self):
            self.assertEqual(False, True)

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.fixtures()
    runner.run()
    exit_code, _ = runner.analyze(write_junit=False)
    assert exit_code == 1

    return


def test_multiple_fixtures():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize(
        [
            McapFixture(path=cmd_vel_only_fixture),
            McapFixture(path=cmd_vel_only_2_fixture),
        ]
    )
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = ["/user/cmd_vel"]

    @run.default()
    class Run:
        def generate_launch_description(self) -> LaunchDescription:
            return LaunchDescription(
                [
                    ExecuteProcess(
                        cmd=[
                            "ros2",
                            "topic",
                            "pub",
                            "/user/cmd_vel",
                            "geometry_msgs/msg/Twist",
                            "{linear: {x: 1.0}, angular: {z: 0.5}}",
                        ],
                        name="topic_pub",
                        output="screen",
                    )
                ]
            )

    @analyze
    class Analyze:
        def test_cmd_vel(self):
            msgs_it = mcap_ros2.reader.read_ros2_messages(self.reader, topics=["/user/cmd_vel"])

            msgs = [msg for msg in msgs_it]
            assert len(msgs) == 1
            assert msgs[0].channel.topic == "/user/cmd_vel"

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    replay_fixtures = runner.fixtures()
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


def test_parametric_sweep():
    test_module = types.ModuleType("test_module")

    @fixtures.parameterize([McapFixture(path=cmd_vel_only_fixture)])
    class Fixtures:
        input_topics = ["/vehicle/cmd_vel"]
        output_topics = ["/user/cmd_vel"]

    @run.parameterize(
        [
            ReplayRunParams(name="run_1_twist_slow", params={"x": 1.0}),
            ReplayRunParams(name="run_2_twist_fast", params={"x": 10.0}),
        ]
    )
    class Run:
        def generate_launch_description(
            self, replay_run_params: ReplayRunParams
        ) -> LaunchDescription:
            print("replay_run_parms")
            twist_msg = {
                "linear": {"x": replay_run_params.params["x"]},
                "angular": {"z": 0.5},
            }
            return LaunchDescription(
                [
                    ExecuteProcess(
                        cmd=[
                            "ros2",
                            "topic",
                            "pub",
                            "/user/cmd_vel",
                            "geometry_msgs/msg/Twist",
                            json.dumps(twist_msg),
                        ],
                        name="topic_pub",
                        output="screen",
                    )
                ]
            )

    @analyze
    class Analyze:
        def test_cmd_vel(self):
            msgs_it = mcap_ros2.reader.read_ros2_messages(self.reader, topics=["/user/cmd_vel"])

            msgs = [msg for msg in msgs_it]
            assert len(msgs) == 1
            assert msgs[0].channel.topic == "/user/cmd_vel"

    test_module.Fixtures = Fixtures
    test_module.Run = Run
    test_module.Analyze = Analyze
    runner = ReplayTestingRunner(test_module)

    runner.fixtures()
    replay_fixtures = runner.run()
    exit_code, _ = runner.analyze()
    assert exit_code == 0

    assert len(replay_fixtures) == 1
    assert len(replay_fixtures[0].run_fixtures) == 2
    return
