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
from mcap_ros2.decoder import DecoderFactory
from mcap_ros2.reader import McapReader, make_reader

# TODO: Figure out how to consolidate the two readers


def get_sequential_mcap_reader(mcap_path: Path):
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(mcap_path), storage_id='mcap'),
        rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'),
    )
    return reader


def get_message_mcap_reader(mcap_path: Path) -> McapReader:
    with mcap_path.open('rb') as file:
        reader = make_reader(file, decoder_factories=[DecoderFactory()])
        return reader
