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

import inspect
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, Optional

import launch
from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from termcolor import colored

from .junit_to_xml import pretty_log_junit_xml, unittest_results_to_xml, write_xml_to_file
from .logging_config import get_logger
from .models import Mcap, ReplayRunParams, ReplayTestingPhase
from .reader import get_sequential_mcap_reader
from .replay_fixture import FILTERED_FIXTURE_NAME, FixtureType, ReplayFixture
from .replay_test_result import ReplayTestResult

_logger_ = get_logger()


class ReplayTestingRunner:
    _replay_results_directory: Path
    _replay_fixtures: list[ReplayFixture]

    def __init__(self, test_module, *, run_id: Optional[str] = None):
        self._replay_fixtures = []
        self._test_module = test_module

        # Check if run_id is truthy (not None and not empty string)
        if run_id:
            self._test_run_uuid = uuid.UUID(run_id)
        else:
            self._test_run_uuid = uuid.uuid4()

        result_base = Path('test_results') if os.environ.get('CI') else Path(tempfile.gettempdir())
        self._replay_directory = result_base / 'replay_testing'

        if not os.access(self._replay_directory, os.W_OK):
            _logger_.error(
                f'No write permission for directory: {self._replay_directory}. Setting to ./test_results/replay_testing'
            )
            self._replay_directory = Path('test_results') / 'replay_testing'

        self._replay_results_directory = self._replay_directory / str(self._test_run_uuid)

        # Only load previous run fixtures if run_id is truthy
        if run_id:
            self._replay_fixtures = self._get_prev_run_fixtures()

    @property
    def run_id(self) -> str:
        """Return the run ID as a string."""
        return str(self._test_run_uuid)

    def _log_stage(self, stage: ReplayTestingPhase, is_start: bool = True):
        stage_name = stage.name
        msg = f'STAGE {stage_name} STARTING' if is_start else f'STAGE {stage_name} COMPLETED'
        padded_msg = f' {msg} '.center(60, '=')
        _logger_.info(colored('=' * len(padded_msg), 'grey'))
        _logger_.info(colored(padded_msg, 'grey'))
        _logger_.info(colored('=' * len(padded_msg), 'grey'))

    def _log_stage_start(self, stage: ReplayTestingPhase):
        self._log_stage(stage, is_start=True)

    def _log_stage_end(self, stage: ReplayTestingPhase):
        self._log_stage(stage, is_start=False)

    def _get_stage_class(self, stage: ReplayTestingPhase):
        # - add exception if multiple preps are defined?
        for _, cls in inspect.getmembers(self._test_module, inspect.isclass):
            phase = cls.__annotations__.get('replay_testing_phase')
            if phase == stage:
                return cls
        raise ValueError(f'No class found for {stage} stage')

    def _get_prev_run_fixtures(self) -> list[ReplayFixture]:
        replay_fixture_list = []
        for dir in self._replay_results_directory.iterdir():
            if not dir.is_dir():
                continue
            replay_fixture = ReplayFixture(self._replay_results_directory, dir.name)

            # Populate the filtered_fixture if it exists
            filtered_mcap_path = dir / FILTERED_FIXTURE_NAME
            if filtered_mcap_path.exists():
                replay_fixture.filtered_fixture = Mcap(path=filtered_mcap_path)

            replay_fixture_list.append(replay_fixture)

        return replay_fixture_list

    def _create_run_launch_description(
        self, filtered_fixture, run_fixture, test_ld: launch.LaunchDescription, run, params: ReplayRunParams
    ) -> launch.LaunchDescription:
        # Define the process action for playing the MCAP file
        cmd = [
            'ros2',
            'bag',
            'play',
            filtered_fixture.path,
            '-r',
            params.runner_args.playback_rate,
        ]

        if params.runner_args is not None and params.runner_args.use_clock:
            cmd.extend(['--clock', '1000'])

        if hasattr(run, 'qos_overrides_yaml'):
            cmd.extend(['--qos-profile-overrides-path', run.qos_overrides_yaml])

        player_action = ExecuteProcess(
            cmd=list(map(str, cmd)),
            name='ros2_bag_player',
            additional_env={'PYTHONUNBUFFERED': '1'},
            output='screen',
        )

        # Event handler to gracefully exit when the process finishes
        on_exit_handler = RegisterEventHandler(
            OnProcessExit(
                target_action=player_action,
                # Shutdown the launch service
                on_exit=[launch.actions.EmitEvent(event=Shutdown())],
            )
        )

        # Launch description with the event handler
        return LaunchDescription([
            ExecuteProcess(
                cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', str(run_fixture.path), '--all'],
                output='screen',
            ),
            test_ld,
            player_action,  # Add the MCAP playback action
            on_exit_handler,  # Add the event handler to shutdown after playback finishes
        ])

    def filter_fixtures(self) -> list[ReplayFixture]:
        self._log_stage_start(ReplayTestingPhase.FIXTURES)

        fixture_cls = self._get_stage_class(ReplayTestingPhase.FIXTURES)
        fixture = fixture_cls()

        self._replay_results_directory.mkdir(parents=True, exist_ok=True)

        # Check for duplicate fixture keys
        fixture_keys = set()
        for fixture_item in fixture_cls.fixture_list:
            if fixture_item.fixture_key in fixture_keys:
                raise ValueError(f'Duplicate fixture key found: {fixture_item.fixture_key}')
            fixture_keys.add(fixture_item.fixture_key)

            replay_fixture = ReplayFixture(self._replay_results_directory, fixture_item.fixture_key)
            replay_fixture.download_input(fixture_item)

            # Input Topics Validation
            reader = replay_fixture.get_reader(FixtureType.INPUT)

            topic_types = reader.get_all_topics_and_types()

            required_input_topics = (
                fixture.required_input_topics if hasattr(fixture, 'required_input_topics') else fixture.input_topics
            )
            expected_output_topics = (
                fixture.expected_output_topics if hasattr(fixture, 'expected_output_topics') else fixture.output_topics
            )

            input_topics_present = []
            for topic_type in topic_types:
                if topic_type.name in required_input_topics:
                    input_topics_present.append(topic_type.name)

            if set(input_topics_present) != set(required_input_topics):
                missing_topics = set(required_input_topics) - set(input_topics_present)
                extra_topics = set(input_topics_present) - set(required_input_topics)

                error_msg = 'Input topics do not match:'
                if missing_topics:
                    error_msg += f'\n  Missing topics: {sorted(missing_topics)}'
                if extra_topics:
                    error_msg += f'\n  Extra topics: {sorted(extra_topics)}'

                _logger_.error(error_msg)
                raise AssertionError('Input topics do not match. Check logs for more information')

            replay_fixture.filter_input(expected_output_topics)

            self._replay_fixtures.append(replay_fixture)

        self._log_stage_end(ReplayTestingPhase.FIXTURES)

        return self._replay_fixtures

    def run(self):
        self._log_stage_start(ReplayTestingPhase.RUN)

        run_cls = self._get_stage_class(ReplayTestingPhase.RUN)
        run = run_cls()

        for replay_fixture in self._replay_fixtures:
            if len(run.parameters) == 0:
                raise ValueError('No parameters found for run')

            if len(replay_fixture.run_fixtures) > 0:
                raise ValueError('Run fixtures already exist')

            _logger_.info(f'Running tests for fixture: {replay_fixture.name}')
            for param in run.parameters:
                run_fixture = replay_fixture.generate_run_fixture(param.name)
                test_launch_description = run.generate_launch_description(param)

                ld = self._create_run_launch_description(
                    replay_fixture.filtered_fixture, run_fixture, test_launch_description, run, param
                )
                launch_service = launch.LaunchService()
                launch_service.include_launch_description(ld)
                launch_service.run()
                _logger_.info('Launch service complete')

            replay_fixture.cleanup_run_fixtures()
            self._log_stage_end(ReplayTestingPhase.RUN)
        return self._replay_fixtures

    def analyze(self, *, write_junit: bool = True) -> tuple[int, Path]:
        self._log_stage_start(ReplayTestingPhase.ANALYZE)
        results: dict[str, list] = {}
        for replay_fixture in self._replay_fixtures:
            results[replay_fixture.name] = []
            analyze_cls: type[Any] = self._get_stage_class(ReplayTestingPhase.ANALYZE)

            for run_fixture in replay_fixture.run_fixtures:
                reader = get_sequential_mcap_reader(run_fixture.path)

                class AnalyzeWithReader(analyze_cls):
                    def setUp(inner_self):
                        super().setUp()  # Call original setUp if it exists
                        inner_self.reader = reader
                        inner_self.suite_classname = analyze_cls.__name__

                suite = unittest.TestLoader().loadTestsFromTestCase(AnalyzeWithReader)
                # TODO: Wrap in error handler?
                result = unittest.TextTestRunner(verbosity=2, resultclass=ReplayTestResult).run(suite)
                results[replay_fixture.name].append({
                    'result': result,
                    'run_fixture_path': str(run_fixture.path),
                    'filtered_fixture_path': str(replay_fixture.filtered_fixture.path),
                })

            # TODO: Maybe return the test class here? Or the results?

        junit_xml_path = self._replay_results_directory / 'results.xml'
        xml_tree = unittest_results_to_xml(
            test_results=results,
            name=self._test_module.__name__,
        )
        pretty_log_junit_xml(xml_tree, junit_xml_path)

        if write_junit:
            write_xml_to_file(xml_tree, junit_xml_path)

        exit_code = 0 if self._was_successful(results) else 1

        self._log_stage_end(ReplayTestingPhase.ANALYZE)
        return (exit_code, junit_xml_path)

    def _was_successful(self, results: dict[str, list]) -> bool:
        for _, fixture_results in results.items():
            for fixture_result in fixture_results:
                if not fixture_result['result'].wasSuccessful():
                    return False

        return True
