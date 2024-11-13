import unittest
from io import BytesIO
import pytest
from junitparser import JUnitXml

import xml.etree.ElementTree as ET

from replay_testing.junit_to_xml import unittest_results_to_xml

# from replay_testing.replay_testing import unittest_results_to_xml


@pytest.fixture
def mock_test_results():
    # Create a mock unittest.TextTestResult object with sample data
    class MockTextTestResult(unittest.TextTestResult):
        def __init__(
            self,
            testsRun=0,
            failures=None,
            errors=None,
            stream=None,
            descriptions=None,
            verbosity=None,
        ):
            # Provide dummy values for required arguments
            if stream is None:
                stream = BytesIO()
            if descriptions is None:
                descriptions = False
            if verbosity is None:
                verbosity = 1
            super().__init__(stream, descriptions, verbosity)
            self.testsRun = testsRun
            self.failures = failures if failures is not None else []
            self.errors = errors if errors is not None else []
            self.successes = []  # Add successes to mock successful test cases

    # Return a list with one or more mock results
    return [
        MockTextTestResult(
            testsRun=5,
            failures=[("test_failure", "traceback")],
            errors=[("test_error", "traceback")],
        ),
        MockTextTestResult(testsRun=3, failures=[], errors=[]),
    ]


def test_unittest_results_to_xml(mock_test_results):
    # Generate the XML element tree from the mock results
    xml_tree = unittest_results_to_xml(test_results=mock_test_results)

    # Use junitparser to load the XML and validate the structure
    junit_xml = JUnitXml.fromstring(
        ET.tostring(xml_tree.getroot(), encoding="utf-8")
    )

    # Check if root element is `testsuites` and contains `testsuite`
    assert (
        junit_xml.name == "replay_test"
    ), "The name attribute of testsuites should be 'replay_test'"

    # Validate the tests, failures, and errors attributes
    total_tests = sum(suite.tests for suite in junit_xml)
    total_failures = sum(suite.failures for suite in junit_xml)
    total_errors = sum(suite.errors for suite in junit_xml)

    assert total_tests == 8, f"Expected 8 tests, got {total_tests}"
    assert total_failures == 1, f"Expected 1 failure, got {total_failures}"
    assert total_errors == 1, f"Expected 1 error, got {total_errors}"

    # Ensure the XML structure contains at least one TestSuite
    assert (
        len(junit_xml) > 0
    ), "Expected at least one testsuite in the XML output"
