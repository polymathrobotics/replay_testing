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

from replay_testing.filter import filter_mcap

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
CMD_VEL_MCAP = FIXTURES_DIR / 'cmd_vel_only.mcap'


def get_mcap_topics(mcap_path: Path) -> list[str]:
    """Get list of topics from an mcap file."""
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(mcap_path), storage_id='mcap'),
        rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'),
    )
    return [topic.name for topic in reader.get_all_topics_and_types()]


def test_filter_mcap_creates_output_file(tmp_path):
    """Test that filter_mcap creates an output file."""
    output_path = tmp_path / 'filtered.mcap'

    filter_mcap(
        input=str(CMD_VEL_MCAP),
        output=str(output_path),
        output_topics=['/vehicle/cmd_vel'],
    )

    assert output_path.exists()


def test_filter_mcap_preserves_matching_topic(tmp_path):
    """Test that filter_mcap preserves messages matching the filter."""
    output_path = tmp_path / 'filtered.mcap'

    filter_mcap(
        input=str(CMD_VEL_MCAP),
        output=str(output_path),
        output_topics=['/vehicle/cmd_vel'],
    )

    topics = get_mcap_topics(output_path)
    assert '/vehicle/cmd_vel' not in topics


def test_filter_mcap_empty_topics_creates_empty_mcap(tmp_path):
    """Test that filtering with non-matching topic creates mcap with no messages."""
    output_path = tmp_path / 'filtered.mcap'

    filter_mcap(
        input=str(CMD_VEL_MCAP),
        output=str(output_path),
        output_topics=['/nonexistent/topic'],
    )

    assert output_path.exists()
    topics = get_mcap_topics(output_path)
    assert '/vehicle/cmd_vel' in topics
