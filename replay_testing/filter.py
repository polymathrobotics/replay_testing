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

import subprocess


def filter_mcap(input, output, output_topics):
    command = [
        'mcap',
        'filter',
        input,
        '-o',
        output,
    ]

    # Filter out topics that will be replayed
    for topic in output_topics:
        command.extend(['-n', topic])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f'Error filtering {input}: {e}')
