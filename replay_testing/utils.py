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
from pathlib import Path


def find_mcap_files(input_dir: Path) -> list[Path]:
    """Recursively find all .mcap files in the input directory."""
    mcap_files = []
    # NOTE: Path.walk is introduced in Python 3.12, we are currently targeting 3.10
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.mcap'):
                mcap_files.append(Path(root) / file)
    return mcap_files
