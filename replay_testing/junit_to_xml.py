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

import datetime
import socket
from pathlib import Path
from xml.etree import ElementTree as ET

from termcolor import colored

from .logging_config import get_logger

_logger_ = get_logger()


def write_xml_to_file(xml_tree: ET.ElementTree, xml_path: Path):
    """Write an XML tree to a file."""
    with xml_path.open('wb') as f:
        xml_tree.write(f, encoding='utf-8', xml_declaration=True)


def _format_file_link(file_path: str):
    """Log a clickable link to a file."""
    file_link = f'file://{file_path}'
    colored_file_link = colored(file_link, 'blue', attrs=['underline'])
    return colored_file_link


def unittest_results_to_xml(*, name='replay_test', test_results=dict) -> ET.ElementTree:
    """Serialize multiple unittest.TestResult objects into a JUnit-compatible XML document."""
    # The `testsuites` element is the root of the XML result.
    test_suites = ET.Element('testsuites')
    test_suites.set('name', name)

    # Hostname and timestamp for additional metadata
    hostname = socket.gethostname()
    timestamp = datetime.datetime.now().isoformat()

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_successes = 0

    _logger_.debug(f'Writing test results to XML: {name}')

    for fixture_results in test_results.values():
        for result_index, test_result in enumerate(fixture_results):
            unittest_result = test_result['result']
            run_fixture_path = test_result['run_fixture_path']
            filtered_fixture_path = test_result['filtered_fixture_path']
            suite = ET.SubElement(test_suites, 'testsuite')
            suite.set('name', f'{name}_suite_{result_index + 1}')
            suite.set('tests', str(unittest_result.testsRun))
            suite.set('failures', str(len(unittest_result.failures)))
            suite.set('errors', str(len(unittest_result.errors)))
            suite.set('hostname', hostname)
            suite.set('timestamp', timestamp)
            suite.set('time', '0')

            # Add fixture paths as properties (standard JUnit XML approach for custom metadata)
            properties = ET.SubElement(suite, 'properties')
            run_fixture_prop = ET.SubElement(properties, 'property')
            run_fixture_prop.set('name', 'run_fixture')
            run_fixture_prop.set('value', run_fixture_path)
            filter_fixture_prop = ET.SubElement(properties, 'property')
            filter_fixture_prop.set('name', 'filter_fixture')
            filter_fixture_prop.set('value', filtered_fixture_path)

            total_tests += unittest_result.testsRun
            total_failures += len(unittest_result.failures)
            total_errors += len(unittest_result.errors)
            total_successes += len(unittest_result.successes)

            for test_case in unittest_result.successes:
                testcase = ET.SubElement(suite, 'testcase')
                testcase.set('name', str(test_case))
                testcase.set('classname', test_case.__annotations__.get('suite_name'))
                testcase.set('time', '0')
                systemout = ET.SubElement(testcase, 'system-out')
                systemout.text = f'[[ATTACHMENT|{run_fixture_path}]]'

            for test_case, traceback in unittest_result.failures:
                testcase = ET.SubElement(suite, 'testcase')
                testcase.set('name', str(test_case))
                testcase.set('classname', test_case.__annotations__.get('suite_name'))
                testcase.set('time', '0')
                failure = ET.SubElement(testcase, 'failure')
                failure.text = traceback
                systemout = ET.SubElement(testcase, 'system-out')
                systemout.text = f'[[ATTACHMENT|{run_fixture_path}]]'

            for test_case, traceback in unittest_result.errors:
                testcase = ET.SubElement(suite, 'testcase')
                testcase.set('name', str(test_case))
                testcase.set('classname', test_case.__annotations__.get('suite_name'))
                testcase.set('time', '0')
                error = ET.SubElement(testcase, 'error')
                error.text = traceback
                systemout = ET.SubElement(testcase, 'system-out')
                systemout.text = f'[[ATTACHMENT|{run_fixture_path}]]'

    # Set the overall counts on the root `testsuites` element
    test_suites.set('tests', str(total_tests))
    test_suites.set('failures', str(total_failures))
    test_suites.set('errors', str(total_errors))

    tree = ET.ElementTree(test_suites)

    return tree


def pretty_log_junit_xml(et: ET.ElementTree, path: Path):
    try:
        root = et.getroot()
        assert root
        # Extract high-level information from the testsuites
        testsuites_name = root.attrib.get('name', 'Unnamed Test Suite')
        total_tests = root.attrib.get('tests', '0')
        total_failures = root.attrib.get('failures', '0')
        total_errors = root.attrib.get('errors', '0')

        path_link = _format_file_link(str(path))
        _logger_.info('=========================================')
        _logger_.info(f'JUnit XML Report ({path_link})')
        # Log high-level summary
        _logger_.info(f'Test Suite: {testsuites_name}')
        _logger_.info(f'Total Tests: {total_tests}')
        _logger_.info(f'Failures: {total_failures}')
        _logger_.info(f'Errors: {total_errors}\n')

        # Iterate over each testsuite element
        for testsuite in root.findall('testsuite'):
            suite_name = testsuite.attrib.get('name', 'Unnamed Test Suite')

            # Extract fixture paths from properties element
            run_fixture = 'N/A'
            filter_fixture = 'N/A'
            properties = testsuite.find('properties')
            if properties is not None:
                for prop in properties.findall('property'):
                    prop_name = prop.attrib.get('name')
                    prop_value = prop.attrib.get('value')
                    if prop_name == 'run_fixture' and prop_value is not None:
                        run_fixture = prop_value
                    elif prop_name == 'filter_fixture' and prop_value is not None:
                        filter_fixture = prop_value

            # Print the suite details
            _logger_.info(f'  Suite: {suite_name}')

            # Print Fixture on a new line as a clickable link
            if run_fixture != 'N/A':
                run_fixture_link = _format_file_link(run_fixture)
                _logger_.info(f'    Run Fixture: {run_fixture_link}')

            if filter_fixture != 'N/A':
                filter_fixture_link = _format_file_link(filter_fixture)
                _logger_.info(f'    Filter Fixture: {filter_fixture_link}')

            # Iterate over each testcase element in the testsuite
            for testcase in testsuite.findall('testcase'):
                test_name = testcase.attrib.get('name', 'Unnamed Test')
                classname = testcase.attrib.get('classname', 'Unknown Class')

                # Print the test case details
                _logger_.info(f'    Test Case: {test_name}')
                _logger_.info(f'      Class: {classname}')

                # Check for failure elements and log details
                failure = testcase.find('failure')
                error = testcase.find('error')
                if failure is not None:
                    failed_txt = colored('FAILED', 'red')
                    _logger_.info(f'      Status: {failed_txt}')
                    _logger_.info(f'      Failure Message: {failure.text.strip() if failure.text else "Not provided"}')
                elif error is not None:
                    error_txt = colored('ERROR', 'red')
                    _logger_.info(f'      Status: {error_txt}')
                    _logger_.info(f'      Error Message: {error.text.strip() if error.text else "Not provided"}')
                else:
                    passed_txt = colored('PASSED', 'green')
                    _logger_.info(f'      Status: {passed_txt}')

                _logger_.info('')  # Newline for better readability
        _logger_.info('=========================================')

    except ET.ParseError as e:
        _logger_.error(f'Failed to parse XML: {e}')
