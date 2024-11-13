import xml.etree.ElementTree as ET
import unittest
import datetime
import socket
import logging
import json

from .replay_test_result import ReplayTestResult
from .logging_config import get_logger

_logger_ = get_logger()


def unittest_results_to_xml(
    *, name="replay_test", test_results=list[ReplayTestResult]
):
    """Serialize multiple unittest.TestResult objects into a JUnit-compatible XML document."""
    # The `testsuites` element is the root of the XML result.
    test_suites = ET.Element("testsuites")
    test_suites.set("name", name)

    # Hostname and timestamp for additional metadata
    hostname = socket.gethostname()
    timestamp = datetime.datetime.now().isoformat()

    total_tests = 0
    total_failures = 0
    total_errors = 0

    _logger_.debug(f"Writing test results to XML: {name}")

    for result_index, replay_test_result in enumerate(test_results):
        suite = ET.SubElement(test_suites, "testsuite")
        suite.set("name", f"{name}_suite_{result_index + 1}")
        suite.set("tests", str(replay_test_result.testsRun))
        suite.set("failures", str(len(replay_test_result.failures)))
        suite.set("errors", str(len(replay_test_result.errors)))
        suite.set("hostname", hostname)
        suite.set("timestamp", timestamp)
        suite.set("time", "0")

        total_tests += replay_test_result.testsRun
        total_failures += len(replay_test_result.failures)
        total_errors += len(replay_test_result.errors)

        for test_case, traceback in replay_test_result.failures:
            testcase = ET.SubElement(suite, "testcase")
            testcase.set("name", str(test_case))
            testcase.set("classname", test_case.__class__.__name__)
            testcase.set("time", "0")
            failure = ET.SubElement(testcase, "failure")
            failure.text = traceback

        for test_case, traceback in replay_test_result.errors:
            testcase = ET.SubElement(suite, "testcase")
            testcase.set("name", str(test_case))
            testcase.set("classname", test_case.__class__.__name__)
            testcase.set("time", "0")
            error = ET.SubElement(testcase, "error")
            error.text = traceback

    # Set the overall counts on the root `testsuites` element
    test_suites.set("tests", str(total_tests))
    test_suites.set("failures", str(total_failures))
    test_suites.set("errors", str(total_errors))

    return ET.ElementTree(test_suites)
