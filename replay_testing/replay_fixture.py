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

import shutil
from pathlib import Path

from .models import Mcap
from .reader import get_message_mcap_reader
from .utils import find_mcap_files


class ReplayFixture:
    input_fixture: Mcap = None
    filtered_fixture: Mcap = None
    run_fixtures: list[Mcap] = None

    base_path: str

    def __init__(self, base_folder: str, input_fixture: Mcap):
        self.run_fixtures = []
        self.base_path = base_folder
        self.input_fixture = input_fixture
        self.filtered_fixture = Mcap(path=self.base_path + '/filtered_fixture.mcap')

    def cleanup_run_fixtures(self):
        for run_fixture in self.run_fixtures:
            mcap_folder = run_fixture.path
            # TODO(troy): cleanup this HACK
            mcap_files = find_mcap_files(mcap_folder)
            if len(mcap_files) == 0:
                raise ValueError(f'No mcap files found in {mcap_folder}')
            mcap_file_path = mcap_files[0]
            new_path = shutil.move(mcap_file_path, Path(mcap_folder).parent)
            shutil.rmtree(mcap_folder)

            run_fixture.path = new_path

    def initialize_run_reader(self):
        self.run_fixture.reader = get_message_mcap_reader(self.run_fixture.path)
