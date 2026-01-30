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

import rosbag2_py


def filter_mcap(input, output, output_topics):
    """Filter out specified topics from an mcap file.

    Args:
        input: Path to input mcap file
        output: Path to output mcap file
        output_topics: List of topic names to exclude from the output
    """
    topics_to_exclude = set(output_topics)

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(input), storage_id='mcap'),
        rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'),
    )

    writer = rosbag2_py.SequentialWriter()
    writer.open(
        rosbag2_py.StorageOptions(uri=output, storage_id='mcap'),
        rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'),
    )

    # Create topics in writer, excluding filtered ones
    for topic_metadata in reader.get_all_topics_and_types():
        if topic_metadata.name not in topics_to_exclude:
            writer.create_topic(topic_metadata)

    # Copy messages, excluding filtered topics
    while reader.has_next():
        topic_name, data, timestamp = reader.read_next()
        if topic_name not in topics_to_exclude:
            writer.write(topic_name, data, timestamp)
