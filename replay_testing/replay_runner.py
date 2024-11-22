import inspect
import os
import difflib


import uuid
from pathlib import Path
import launch
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    ExecuteProcess,
    RegisterEventHandler,
)

from termcolor import colored
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown

import unittest

from .reader import get_sequential_mcap_reader, get_message_mcap_reader
from .models import ReplayTestingPhase, McapFixture
from .filter import filter_mcap
from .replay_fixture import ReplayFixture
from .logging_config import get_logger
from .replay_test_result import ReplayTestResult
from .junit_to_xml import unittest_results_to_xml, write_xml_to_file, pretty_log_junit_xml

_logger_ = get_logger()


class ReplayTestingRunner:
    _replay_results_directory: str
    _replay_fixtures: list[ReplayFixture] = None
    # todo: Validate input in test_module

    def __init__(self, test_module):
        self._replay_fixtures = []
        self._test_module = test_module
        # TODO: Change to /tmp/replay_testing/{test_run_uuid}
        self._test_run_uuid = uuid.uuid4()

        # For Gitlab CI. TODO(troy): This should just be an env variable set by .gitlab-ci.yml
        if os.environ.get("CI"):
            self._replay_results_directory = (
                f"test_results/replay_testing/{self._test_run_uuid}"
            )
        else:
            self._replay_results_directory = (
                f"/tmp/replay_testing/{self._test_run_uuid}"
            )

    def _log_stage(self, stage: ReplayTestingPhase, is_start: bool = True):
        stage_name = stage.name
        msg = f"STAGE {stage_name} STARTING" if is_start else f"STAGE {stage_name} COMPLETED"
        padded_msg = f" {msg} ".center(60, "=")
        _logger_.info(colored("=" * len(padded_msg), "grey"))
        _logger_.info(colored(padded_msg, "grey"))
        _logger_.info(colored("=" * len(padded_msg), "grey"))

    def _log_stage_start(self, stage: str):
        self._log_stage(stage, is_start=True)

    def _log_stage_end(self, stage: str):
        self._log_stage(stage, is_start=False)

    def _get_stage_class(self, stage: ReplayTestingPhase):
        # - add exception if multiple preps are defined?
        for _, cls in inspect.getmembers(self._test_module, inspect.isclass):
            phase = cls.__annotations__.get("replay_testing_phase")
            if phase == stage:
                return cls
        raise ValueError(f"No class found for {stage} stage")

    def _create_run_launch_description(
        self, filtered_fixture, run_fixture, test_ld: launch.LaunchDescription, run
    ) -> launch.LaunchDescription:
        # Define the process action for playing the MCAP file
        cmd = [
            "ros2",
            "bag",
            "play",
            filtered_fixture.path,
            "--clock",
            "10000",
        ]

        if hasattr(run, "qos_overrides_yaml"):
            cmd.extend(["--qos-profile-overrides-path",
                       run.qos_overrides_yaml])

        player_action = ExecuteProcess(
            cmd=cmd,
            name="ros2_bag_player",
            additional_env={"PYTHONUNBUFFERED": "1"},
            output="screen",
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
        return LaunchDescription(
            [
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        PathJoinSubstitution(
                            [
                                FindPackageShare("mcap_recorder"),
                                "launch/recorder.launch.py",
                            ]
                        )
                    ),
                    launch_arguments={
                        "recording_directory": f"{Path(run_fixture.path).parent}",
                        "mcap_filename": f"{Path(run_fixture.path).stem}",
                    }.items(),
                ),
                test_ld,
                player_action,  # Add the MCAP playback action
                on_exit_handler,  # Add the event handler to shutdown after playback finishes
            ]
        )

    def fixtures(self) -> str:
        self._log_stage_start(ReplayTestingPhase.FIXTURES)

        # todo: Add exception handling
        fixture_cls = self._get_stage_class(ReplayTestingPhase.FIXTURES)
        fixture = fixture_cls()

        # Prepare Directories
        os.makedirs(self._replay_results_directory)

        # MCAP Assertions
        for fixture_item in fixture_cls.fixture_list:
            assert os.path.exists(
                fixture_item.path
            ), "Fixture path does not exist"
            assert (
                os.path.splitext(fixture_item.path)[1] == ".mcap"
            ), "Fixture path is not an .mcap file"

            # Input Topics Validation
            reader = get_sequential_mcap_reader(fixture_item.path)

            topic_types = reader.get_all_topics_and_types()

            input_topics_present = []
            for topic_type in topic_types:
                if topic_type.name in fixture.input_topics:
                    input_topics_present.append(topic_type.name)

            if set(input_topics_present) != set(fixture.input_topics):
                diff = difflib.ndiff(
                    input_topics_present, fixture.input_topics
                )
                diff_str = "\n".join(diff)
                _logger_.error(f"Input topics do not match. Diff: {diff_str}")
                raise AssertionError(
                    "Input topics do not match. Check logs for more information"
                )

            current_fixture_results_dir = (
                self._replay_results_directory
                + f"/{Path(fixture_item.path).stem}"
            )
            os.makedirs(current_fixture_results_dir)
            replay_fixture = ReplayFixture(
                current_fixture_results_dir, fixture_item
            )
            # Run Filter
            # todo: add error handling
            filter_mcap(
                replay_fixture.input_fixture.path,
                replay_fixture.filtered_fixture.path,
                fixture.output_topics,
            )

            self._replay_fixtures.append(replay_fixture)

        self._log_stage_end(ReplayTestingPhase.FIXTURES)

        return self._replay_fixtures

    def run(self):
        self._log_stage_start(ReplayTestingPhase.RUN)

        run_cls = self._get_stage_class(ReplayTestingPhase.RUN)
        run = run_cls()

        for replay_fixture in self._replay_fixtures:
            if len(run.parameters) == 0:
                raise ValueError("No parameters found for run")

            if len(replay_fixture.run_fixtures) > 0:
                raise ValueError("Run fixtures already exist")

            for param in run.parameters:
                run_fixture = McapFixture(
                    path=replay_fixture.base_path + f"/runs/{param.name}"
                )
                replay_fixture.run_fixtures.append(run_fixture)

                test_launch_description = run.generate_launch_description(
                    param
                )

                ld = self._create_run_launch_description(
                    replay_fixture.filtered_fixture,
                    run_fixture,
                    test_launch_description,
                    run
                )
                launch_service = launch.LaunchService()
                launch_service.include_launch_description(ld)
                launch_service.run()

            # TODO(troy): Pretty please emove this hack please

            replay_fixture.cleanup_run_fixtures()
            self._log_stage_end(ReplayTestingPhase.RUN)
        return self._replay_fixtures

    def analyze(self, *, write_junit: bool = True) -> tuple[int, str]:
        self._log_stage_start(ReplayTestingPhase.ANALYZE)
        results = {}
        for replay_fixture in self._replay_fixtures:
            results[replay_fixture.input_fixture.path] = []
            analyze_cls = self._get_stage_class(ReplayTestingPhase.ANALYZE)

            for run_fixture in replay_fixture.run_fixtures:
                reader = get_message_mcap_reader(run_fixture.path)

                class AnalyzeWithReader(analyze_cls):
                    def setUp(inner_self):
                        super().setUp()  # Call original setUp if it exists
                        inner_self.reader = reader
                        inner_self.suite_classname = analyze_cls.__name__
                suite = unittest.TestLoader().loadTestsFromTestCase(
                    AnalyzeWithReader
                )
                # TODO: Wrap in error handler?
                result = unittest.TextTestRunner(
                    verbosity=2,
                    resultclass=ReplayTestResult).run(suite)
                results[replay_fixture.input_fixture.path].append({
                    "result": result,
                    "run_fixture_path": run_fixture.path,
                    "filtered_fixture_path": replay_fixture.filtered_fixture.path
                })

            # TODO: Maybe return the test class here? Or the results?

        junit_xml_path = self._replay_results_directory + "/results.xml"
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

    def _was_successful(self, results: dict[str, list[tuple[ReplayTestResult, McapFixture]]]) -> bool:
        for _, fixture_results in results.items():
            for fixture_result in fixture_results:
                if not fixture_result["result"].wasSuccessful():
                    return False

        return True
