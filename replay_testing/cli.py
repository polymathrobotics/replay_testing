#!/usr/bin/env python3

import argparse
import importlib.util
import logging
import os
import sys

from replay_testing import ReplayTestingRunner, unittest_results_to_xml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Console output
    ]
)

_logger_ = logging.getLogger(__name__)


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
    _logger_.info("Running replay test file '{}'".format(
        args.replay_test_file))
    # Load the test file as a module and make sure it has the required
    # components to run it as a replay test
    _logger_.debug(
        "Loading tests from file '{}'".format(args.replay_test_file)
    )
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
    results = runner.analyze()

    if args.xmlpath:
        try:
            xml_report = unittest_results_to_xml(
                test_results=results,
                name="{}.{}".format(
                    args.package_name, replay_test_file_basename
                ),
            )
            xml_report.write(
                args.xmlpath, encoding="utf-8", xml_declaration=True
            )
        except Exception as e:
            print("Error writing xUnit report: {}".format(e))
            return 1
    if not all([result.wasSuccessful() for result in results]):
        return 1
    return 0


def main():
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
