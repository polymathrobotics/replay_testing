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

import argparse
import importlib.util
import logging
import os
import shutil
import sys
from pathlib import Path

from replay_testing import ReplayTestingRunner, get_logger

_logger_ = get_logger()


def _load_python_file_as_module(test_module_name, python_file_path):
    """Load a given Python replay file (by path) as a Python module."""
    spec = importlib.util.spec_from_file_location(test_module_name, python_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_env_file(env_file_path: Path):
    """Load environment variables from a file."""
    if not env_file_path.is_file():
        raise FileNotFoundError(f"Environment file '{env_file_path}' does not exist")

    _logger_.info(f'Loading environment variables from {env_file_path}')

    with env_file_path.open('r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE format
            if '=' not in line:
                _logger_.warning(f'Skipping invalid line {line_num} in {env_file_path}: {line}')
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            # Set environment variable
            os.environ[key] = value
            _logger_.debug(f'Set {key}={value}')

    _logger_.info(f'Loaded environment variables from {env_file_path}')


def add_arguments(parser):
    """Add arguments to the CLI parser."""
    parser.add_argument('replay_test_file', type=Path, help='Path to the replay test.')

    parser.add_argument(
        '--package-name',
        action='store',
        default=None,
        help='Name of the package the test is in. Useful to aggregate xUnit reports.',
    )

    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help='Run with verbose output',
    )
    parser.add_argument(
        '-s',
        '--show-args',
        '--show-arguments',
        action='store_true',
        default=False,
        help='Show arguments that may be given to the replay test.',
    )

    parser.add_argument(
        '--analyze',
        action='store',
        default=None,
        help='Run ID of a previous run to only perform analysis on. Useful for re-analyzing a previous run while iterating on analyze logic.',
    )

    parser.add_argument(
        '--junit-xml',
        action='store',
        dest='xmlpath',
        default=None,
        help='Do write xUnit reports to specified path.',
    )

    parser.add_argument(
        '--env',
        action='store',
        dest='env_file',
        default=None,
        help='Path to environment file to load variables from.',
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description='replay integration testing tool.')
    add_arguments(parser)
    return parser, parser.parse_args()


def run(parser, args):
    # Load environment file if specified
    if args.env_file:
        try:
            # TODO(troy): Replace with dotenv package
            _load_env_file(Path(args.env_file))
        except Exception as e:
            parser.error(f'Failed to load environment file: {e}')

    # Load the test file as a module and make sure it has the required
    # components to run it as a replay test
    if not args.replay_test_file.is_file():
        # Note to future reader: parser.error also exits as a side effect
        parser.error(f"Test file '{args.replay_test_file}' does not exist")

    if not args.package_name:
        args.package_name = args.replay_test_file.stem

    test_module = _load_python_file_as_module(args.package_name, args.replay_test_file.absolute())

    runner = ReplayTestingRunner(test_module, run_id=args.analyze)

    if not args.analyze:
        runner.filter_fixtures()
        runner.run()

    exit_code, junit_xml_path = runner.analyze()

    # Each individual test case should have its own xUnit report in the
    # corresponding /replay_testing directory.  However for systems like Gitlab
    # CI, we need to colocate results at the top level.
    if args.xmlpath:
        try:
            shutil.copy(junit_xml_path, args.xmlpath)
        except Exception as e:
            print('Error copying xUnit report: {}'.format(e))
            return 1

    return exit_code


def main():
    _logger_.info('Starting replay test runner')
    parser, args = parse_arguments()

    if args.verbose:
        _logger_.setLevel(logging.DEBUG)
        _logger_.debug('Running with verbose output')

    try:
        sys.exit(run(parser, args))
    except Exception as e:
        parser.error(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
