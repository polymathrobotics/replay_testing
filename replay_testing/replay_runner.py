# Copyright 2025 Polymath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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

    def __init__(self, test_module, *, run_id: Optional[str] = None, output_dir: Optional[str] = None):
        self._replay_fixtures = []
        self._test_module = test_module

        # Check if run_id is truthy (not None and not empty string)
        if run_id:
            self._test_run_uuid = uuid.UUID(run_id)
        else:
            self._test_run_uuid = uuid.uuid4()

        if output_dir:
            result_base = Path(output_dir)
        elif os.environ.get('CI'):
            result_base = Path('test_results')
        else:
            result_base = Path(tempfile.gettempdir())
        self._replay_directory = result_base / 'replay_testing'

        # os.access() is False for a path that does not exist yet, so without
        # this the probe below would silently redirect every run to ./test_results.
        try:
            self._replay_directory.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            _logger_.error(f'Could not create {self._replay_directory}: {e}')

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
        self,
        filtered_fixture,
        run_fixture,
        test_ld: launch.LaunchDescription,
        run,
        params: ReplayRunParams,
        expected_output_topics: Optional[list] = None,
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

        recorder_action = ExecuteProcess(
            cmd=[
                'ros2',
                'bag',
                'record',
                '-s',
                'mcap',
                '-o',
                str(run_fixture.path),
                '--all',
                '--storage-preset-profile',
                'zstd_fast',
            ],
            output='screen',
        )

        # Hold the player until the stack under test is publishing, so a short
        # fixture cannot finish before its output topics even exist.
        gate = self._wait_for_stack_action(expected_output_topics, params)
        if gate is not None:
            start_playback = [
                gate,
                RegisterEventHandler(OnProcessExit(target_action=gate, on_exit=[player_action])),
            ]
        else:
            start_playback = [player_action]

        ld = LaunchDescription([recorder_action, test_ld, *start_playback])

        if not params.ignore_playback_finish:
            # Event handler to gracefully exit when the process finishes
            on_exit_handler = RegisterEventHandler(
                OnProcessExit(
                    target_action=player_action,
                    # Shutdown the launch service
                    on_exit=[launch.actions.EmitEvent(event=Shutdown())],
                )
            )

            ld.add_action(on_exit_handler)

        return ld

    @staticmethod
    def _wait_for_stack_action(expected_output_topics, params: ReplayRunParams):
        """The process that gates playback, or None when not gating."""
        runner_args = params.runner_args
        if not runner_args.wait_for_stack:
            return None

        return ExecuteProcess(
            cmd=[
                'ros2',
                'run',
                'replay_testing',
                'replay_test_wait_for_stack',
                *expected_output_topics,
                '--timeout',
                str(runner_args.wait_for_stack_timeout),
                '--grace',
                str(runner_args.wait_for_stack_grace),
            ],
            name='wait_for_stack',
            output='screen',
        )

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

            declared = {topic_type.name for topic_type in topic_types}
            missing_topics = set(required_input_topics) - declared

            if missing_topics:
                _logger_.error(f'Required input topics not in the bag: {sorted(missing_topics)}')
                raise AssertionError('Required input topics missing. Check logs for more information')

            # A topic may appear in the bag without messages. This isn't fatal:
            # it means a silent sensor was correctly recorded. Only later analysis decides if that's an issue.
            empty_topics = self._topics_without_messages(replay_fixture, sorted(set(required_input_topics) & declared))
            if empty_topics:
                _logger_.warning(f'Required input topics declared but empty: {sorted(empty_topics)}')

            replay_fixture.filter_input(expected_output_topics)

            self._replay_fixtures.append(replay_fixture)

        self._log_stage_end(ReplayTestingPhase.FIXTURES)

        return self._replay_fixtures

    @staticmethod
    def _topics_without_messages(replay_fixture: ReplayFixture, topics: list[str]) -> list[str]:
        """Which of these topics are declared in the bag but carry no messages."""
        if not topics:
            return []

        counts = dict.fromkeys(topics, 0)
        reader = replay_fixture.get_reader(FixtureType.INPUT)
        while reader.has_next():
            topic_name, _, _ = reader.read_next()
            if topic_name in counts:
                counts[topic_name] += 1

        return [topic for topic, count in counts.items() if count == 0]

    def run(self):
        self._log_stage_start(ReplayTestingPhase.RUN)

        run_cls = self._get_stage_class(ReplayTestingPhase.RUN)
        run = run_cls()

        fixture_cls = self._get_stage_class(ReplayTestingPhase.FIXTURES)
        expected_output_topics = getattr(
            fixture_cls, 'expected_output_topics', getattr(fixture_cls, 'output_topics', [])
        )

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
                    replay_fixture.filtered_fixture,
                    run_fixture,
                    test_launch_description,
                    run,
                    param,
                    expected_output_topics,
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

                class AnalyzeWithReader(analyze_cls):
                    def setUp(inner_self):
                        super().setUp()  # Call original setUp if it exists
                        # Each test needs a fresh reader since readers can't rewind.
                        inner_self.reader = get_sequential_mcap_reader(run_fixture.path)
                        inner_self.run_fixture_path = run_fixture.path
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
