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
from enum import Enum
from pathlib import Path

from .filter import filter_mcap
from .fixtures import BaseFixture
from .models import Mcap
from .reader import get_sequential_mcap_reader
from .utils import find_mcap_files


class FixtureType(Enum):
    INPUT = 1
    FILTERED = 2
    RUN = 3


FILTERED_FIXTURE_NAME = 'filtered.mcap'


class ReplayFixture:
    """Class to manage replay fixtures for testing."""

    input_fixture: Mcap
    filtered_fixture: Mcap
    run_fixtures: list[Mcap]

    base_path: Path

    def __init__(self, replay_results_dir: Path, fixture_key: str):
        self.replay_results_dir = replay_results_dir
        self.fixture_key = fixture_key
        self.run_fixtures = self._get_previous_run_fixtures()

    @property
    def name(self) -> str:
        return self.fixture_key

    @property
    def path(self) -> Path:
        return self.replay_results_dir / self.fixture_key

    def download_input(self, fixture: BaseFixture):
        """Download the input fixture to the base path."""
        if not isinstance(fixture, BaseFixture):
            raise TypeError('Fixture must be an instance of BaseFixture')

        try:
            self.path.mkdir(parents=True, exist_ok=True)
            self.input_fixture = fixture.download(self.path)
            if not self.input_fixture or not self.input_fixture.path or not Path(self.input_fixture.path).exists():
                raise ValueError('Downloaded fixture is invalid or has no path')

        except Exception as e:
            raise RuntimeError(f'Failed to download input fixture: {e}')

    def filter_input(self, expected_output_topics: list[str]):
        filtered_mcap_path = self.path / FILTERED_FIXTURE_NAME

        try:
            filter_mcap(
                self.input_fixture.path,
                str(filtered_mcap_path),
                expected_output_topics,
            )
            self.filtered_fixture = Mcap(path=filtered_mcap_path)
        except Exception as e:
            raise RuntimeError(f'Failed to filter input fixture: {e}')

    def get_reader(self, type: FixtureType = FixtureType.INPUT):
        """Get a sequential MCAP reader for the specified fixture type."""
        if type == FixtureType.INPUT:
            return get_sequential_mcap_reader(self.input_fixture.path)
        elif type == FixtureType.FILTERED:
            return get_sequential_mcap_reader(self.filtered_fixture.path)
        else:
            raise ValueError(f'Unsupported fixture type: {type}')

    def generate_run_fixture(self, key) -> Mcap:
        """Add a run fixture to the list."""
        run_fixture = Mcap(path=self.path / 'runs' / f'run_{key}_{self.name}')
        self.run_fixtures.append(run_fixture)
        return run_fixture

    def _get_previous_run_fixtures(self) -> list:
        """Check for existing run fixtures in the runs directory. Returns empty list if none found."""
        run_fixtures = []
        runs_dir = self.path / 'runs'
        if runs_dir.exists() and runs_dir.is_dir():
            for run_fixture in runs_dir.iterdir():
                if run_fixture.is_file():
                    run_fixtures.append(Mcap(path=run_fixture))
        return run_fixtures

    def cleanup_run_fixtures(self):
        """
        Move the generated MCAP files from the run fixture directories to the parent directory
        and remove the now-empty run fixture directories.
        """
        for run_fixture in self.run_fixtures:
            mcap_folder = run_fixture.path
            mcap_files = find_mcap_files(mcap_folder)
            if len(mcap_files) == 0:
                raise ValueError(f'No mcap files found in {mcap_folder}')
            mcap_file_path = mcap_files[0]
            new_path = Path(shutil.move(mcap_file_path, mcap_folder.parent))
            shutil.rmtree(mcap_folder)

            run_fixture.path = new_path
