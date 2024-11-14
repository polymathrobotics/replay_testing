import xml.etree.ElementTree as ET
import unittest
import datetime
import socket
import logging
import json
from termcolor import colored
from xml.dom import minidom

from .replay_test_result import ReplayTestResult
from .logging_config import get_logger
from .models import ReplayTestingPhase, McapFixture

_logger_ = get_logger()


def write_xml_to_file(xml_tree: ET.ElementTree, xml_path: str):
    """Write an XML tree to a file."""
    with open(xml_path, "wb") as f:
        xml_tree.write(f, encoding="utf-8", xml_declaration=True)


def _format_file_link(file_path: str):
    """Log a clickable link to a file."""
    file_link = f"file://{file_path}"
    colored_file_link = colored(file_link, "blue", attrs=["underline"])
    return colored_file_link


def unittest_results_to_xml(
    *, name="replay_test", test_results=dict
) -> ET:
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
    total_successes = 0

    _logger_.debug(f"Writing test results to XML: {name}")

    for _, fixture_results in test_results.items():
        for result_index, test_result in enumerate(fixture_results):
            unittest_result = test_result["result"]
            run_fixture_path = test_result["run_fixture_path"]
            filtered_fixture_path = test_result["filtered_fixture_path"]
            suite = ET.SubElement(test_suites, "testsuite")
            suite.set("name", f"{name}_suite_{result_index + 1}")
            suite.set("tests", str(unittest_result.testsRun))
            suite.set("failures", str(len(unittest_result.failures)))
            suite.set("errors", str(len(unittest_result.errors)))
            suite.set("hostname", hostname)
            suite.set("timestamp", timestamp)
            suite.set("time", "0")
            suite.set("run_fixture", run_fixture_path)
            suite.set("filter_fixture", filtered_fixture_path)

            total_tests += unittest_result.testsRun
            total_failures += len(unittest_result.failures)
            total_errors += len(unittest_result.errors)
            total_successes += len(unittest_result.successes)

            for test_case in unittest_result.successes:
                testcase = ET.SubElement(suite, "testcase")
                testcase.set("name", str(test_case))
                testcase.set(
                    "classname", test_case.__annotations__.get("suite_name"))
                testcase.set("time", "0")
                systemout = ET.SubElement(testcase, "system-out")
                systemout.text = f"[[ATTACHMENT|{run_fixture_path}]]"

            for test_case, traceback in unittest_result.failures:
                testcase = ET.SubElement(suite, "testcase")
                testcase.set("name", str(test_case))
                testcase.set(
                    "classname", test_case.__annotations__.get("suite_name"))
                testcase.set("time", "0")
                failure = ET.SubElement(testcase, "failure")
                failure.text = traceback
                systemout = ET.SubElement(testcase, "system-out")
                systemout.text = f"[[ATTACHMENT|{run_fixture_path}]]"

            for test_case, traceback in unittest_result.errors:
                testcase = ET.SubElement(suite, "testcase")
                testcase.set("name", str(test_case))
                testcase.set(
                    "classname", test_case.__annotations__.get("suite_name"))
                testcase.set("time", "0")
                error = ET.SubElement(testcase, "error")
                error.text = traceback
                systemout = ET.SubElement(testcase, "system-out")
                systemout.text = f"[[ATTACHMENT|{run_fixture_path}]]"

    # Set the overall counts on the root `testsuites` element
    test_suites.set("tests", str(total_tests))
    test_suites.set("successes", str(total_successes))
    test_suites.set("failures", str(total_failures))
    test_suites.set("errors", str(total_errors))

    tree = ET.ElementTree(test_suites)

    return tree


def pretty_log_junit_xml(et: ET, path: str):
    try:
        root = et.getroot()
        # Extract high-level information from the testsuites
        testsuites_name = root.attrib.get("name", "Unnamed Test Suite")
        total_tests = root.attrib.get("tests", "0")
        total_successes = root.attrib.get("successes", "0")
        total_failures = root.attrib.get("failures", "0")
        total_errors = root.attrib.get("errors", "0")

        path_link = _format_file_link(path)
        _logger_.info("=========================================")
        _logger_.info(f"JUnit XML Report ({path_link})")
        # Log high-level summary
        _logger_.info(f"Test Suite: {testsuites_name}")
        _logger_.info(f"Total Tests: {total_tests}")
        _logger_.info(f"Successes: {total_successes}")
        _logger_.info(f"Failures: {total_failures}")
        _logger_.info(f"Errors: {total_errors}\n")

        # Iterate over each testsuite element
        for testsuite in root.findall("testsuite"):
            suite_name = testsuite.attrib.get("name", "Unnamed Test Suite")
            run_fixture = testsuite.attrib.get("run_fixture", "N/A")
            filter_fixture = testsuite.attrib.get("filter_fixture", "N/A")

            # Print the suite details
            _logger_.info(f"  Suite: {suite_name}")

            # Print Fixture on a new line as a clickable link
            if run_fixture != "N/A":
                run_fixture_link = _format_file_link(run_fixture)
                _logger_.info(f"    Run Fixture: {run_fixture_link}")

            if filter_fixture != "N/A":
                filter_fixture_link = _format_file_link(filter_fixture)
                _logger_.info(f"    Filter Fixture: {filter_fixture_link}")

            # Iterate over each testcase element in the testsuite
            for testcase in testsuite.findall("testcase"):
                test_name = testcase.attrib.get("name", "Unnamed Test")
                classname = testcase.attrib.get("classname", "Unknown Class")

                # Print the test case details
                _logger_.info(f"    Test Case: {test_name}")
                _logger_.info(f"      Class: {classname}")

                # Check for failure elements and log details
                failure = testcase.find("failure")
                if failure is not None:
                    failed_txt = colored("FAILED", 'red')
                    _logger_.info(f"      Status: {failed_txt}")
                    _logger_.info(
                        f"      Failure Message: {failure.text.strip()}")
                else:
                    passed_txt = colored("PASSED", 'green')
                    _logger_.info(f"      Status: {passed_txt}")

                _logger_.info("")  # Newline for better readability
        _logger_.info("=========================================")

    except ET.ParseError as e:
        _logger_.error(f"Failed to parse XML: {e}")
