from replay_testing import (
    fixtures,
    run,
    analyze,
    McapFixture,
    ReplayRunParams,
)
from launch import LaunchDescription
from launch.actions import ExecuteProcess

import json
import mcap_ros2.reader
import pathlib
from ament_index_python.packages import get_package_share_directory
import os

replay_testing_dir = get_package_share_directory("replay_testing")

cmd_vel_only_fixture = os.path.join(
    replay_testing_dir, "test", "fixtures", "cmd_vel_only.mcap"
)
cmd_vel_only_2_fixture = os.path.join(
    replay_testing_dir, "test", "fixtures", "cmd_vel_only_2.mcap"
)


@fixtures.parameterize(
    [
        McapFixture(path=cmd_vel_only_fixture),
        McapFixture(path=cmd_vel_only_2_fixture),
    ]
)
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
        msgs_it = mcap_ros2.reader.read_ros2_messages(
            self.reader, topics=["/user/cmd_vel"]
        )

        msgs = [msg for msg in msgs_it]
        assert len(msgs) == 1
        assert msgs[0].channel.topic == "/user/cmd_vel"
