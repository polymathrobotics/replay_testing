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
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def get_sequential_mcap_reader(mcap_path: Path):
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(mcap_path), storage_id='mcap'),
        rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'),
    )
    return reader


def read_messages(reader: rosbag2_py.SequentialReader, topics: list[str]):
    """
    Read and deserialize messages from specific topics in an MCAP file.

    Args:
        reader: SequentialReader instance from get_sequential_mcap_reader
        topics: List of topic names to read from

    Yields:
        Tuples of (topic_name, ros_msg, timestamp) where ros_msg is the deserialized ROS2 message
    """
    topic_set = set(topics) if topics else None

    # Get topic type map
    topic_types = {}
    for topic_metadata in reader.get_all_topics_and_types():
        topic_types[topic_metadata.name] = topic_metadata.type

    while reader.has_next():
        topic_name, data, timestamp = reader.read_next()

        # Filter by topic if topics list is provided
        if topic_set is None or topic_name in topic_set:
            # Deserialize the message
            msg_type = get_message(topic_types[topic_name])
            msg = deserialize_message(data, msg_type)
            yield (topic_name, msg, timestamp)
