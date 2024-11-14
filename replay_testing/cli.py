#!/usr/bin/env python3

import argparse
import importlib.util
import logging
import os
import sys
import shutil

from replay_testing import ReplayTestingRunner, get_logger

_logger_ = get_logger()


def _load_python_file_as_module(test_module_name, python_file_path):
    """Load a given Python replay file (by path) as a Python module."""
    spec = importlib.util.spec_from_file_location(
        test_module_name, python_file_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_arguments(parser):
    """Add arguments to the CLI parser."""
    parser.add_argument("replay_test_file", help="Path to the replay test.")

    parser.add_argument(
        "--package-name",
        action="store",
        default=None,
        help="Name of the package the test is in. Useful to aggregate xUnit reports.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Run with verbose output",
    )
    parser.add_argument(
        "-s",
        "--show-args",
        "--show-arguments",
        action="store_true",
        default=False,
        help="Show arguments that may be given to the replay test.",
    )

    parser.add_argument(
        "--junit-xml",
        action="store",
        dest="xmlpath",
        default=None,
        help="Do write xUnit reports to specified path.",
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="replay integration testing tool."
    )
    add_arguments(parser)
    return parser, parser.parse_args()


def run(parser, args):
    # Load the test file as a module and make sure it has the required
    # components to run it as a replay test
    if not os.path.isfile(args.replay_test_file):
        # Note to future reader: parser.error also exits as a side effect
        parser.error(
            "Test file '{}' does not exist".format(args.replay_test_file)
        )

    args.replay_test_file = os.path.abspath(args.replay_test_file)
    replay_test_file_basename = os.path.splitext(
        os.path.basename(args.replay_test_file)
    )[0]
    if not args.package_name:
        args.package_name = replay_test_file_basename

    test_module = _load_python_file_as_module(
        args.package_name, args.replay_test_file
    )

    runner = ReplayTestingRunner(test_module)

    runner.fixtures()
    runner.run()
    exit_code, junit_xml_path = runner.analyze()

    # Each individual test case should have its own xUnit report in the
    # corresponding /replay_testing directory.  However for systems like Gitlab
    # CI, we need to colocate results at the top level.
    if args.xmlpath:
        try:
            shutil.copy(junit_xml_path, args.xmlpath)
        except Exception as e:
            print("Error copying xUnit report: {}".format(e))
            return 1

    return exit_code


def main():
    _logger_.info("Starting replay test runner")
    parser, args = parse_arguments()

    if args.verbose:
        _logger_.setLevel(logging.DEBUG)
        _logger_.debug("Running with verbose output")

    try:
        sys.exit(run(parser, args))
    except Exception as e:
        parser.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
