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

import socket
from unittest.mock import Mock

from replay_testing.junit_to_xml import unittest_results_to_xml
from replay_testing.replay_test_result import ReplayTestResult


def test_unittest_results_to_xml():
    # Create a ReplayTestResult object and simulate some results
    replay_result = ReplayTestResult()
    replay_result.testsRun = 2
    replay_result.failures = []
    replay_result.errors = []
    replay_result.successes = [Mock(name='test_case_1'), Mock(name='test_case_2')]

    # Customize test mocks to include annotations by directly setting __annotations__
    for success_test in replay_result.successes:
        success_test.__annotations__ = {'suite_name': 'suite_1'}

    # Test input data for the function
    test_results = {
        'test_fixture': [
            {
                'result': replay_result,
                'run_fixture_path': '/path/to/run_fixture',
                'filtered_fixture_path': '/path/to/filtered_fixture',
            }
        ]
    }

    # Call the function
    xml_tree = unittest_results_to_xml(name='replay_test', test_results=test_results)

    # Verify the XML structure and some content
    root = xml_tree.getroot()
    assert root.tag == 'testsuites'
    assert root.get('name') == 'replay_test'
    assert root.get('tests') == '2'
    assert root.get('failures') == '0'
    assert root.get('errors') == '0'

    # Check the first testsuite
    testsuite = root.find('testsuite')
    assert testsuite is not None
    assert testsuite.get('name') == 'replay_test_suite_1'
    assert testsuite.get('tests') == '2'
    assert testsuite.get('failures') == '0'
    assert testsuite.get('errors') == '0'
    assert testsuite.get('hostname') == socket.gethostname()
    assert testsuite.get('timestamp') is not None

    # Check each testcase in testsuite
    testcases = testsuite.findall('testcase')
    assert len(testcases) == 2
