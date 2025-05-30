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

import os
import sys
import xml.etree.ElementTree as ET

import pytest
from ament_index_python.packages import get_package_share_directory

from replay_testing.cli import main

replay_testing_dir = get_package_share_directory('replay_testing')


def test_cli_with_replay_test_file_argument():
    replay_file_path = os.path.join(replay_testing_dir, 'test', 'replay_tests', 'basic_replay.py')

    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', replay_file_path]

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()

    # Check that exit code is 0 (indicating success)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_cli_xml_output_success(capsys):
    xml_path = os.path.join('/tmp', 'test.xml')
    replay_file_path = os.path.join(replay_testing_dir, 'test', 'replay_tests', 'basic_replay.py')

    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', replay_file_path, '--junit-xml', xml_path, '--verbose']

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()

    # Check that exit code is 0 (indicating success)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 0

    junit_xml = ET.parse(xml_path)
    root = junit_xml.getroot()

    # Assert top level name
    assert root.tag == 'testsuites'

    # Assert on test suites within <testsuites> in a loop
    for testsuite in root.iter('testsuite'):
        assert testsuite.get('tests') == '1'
        for tescase in testsuite.iter('testcase'):
            assert 'test_cmd_vel' in tescase.get('name')
            assert tescase.get('classname') == 'AnalyzeBasicReplay'
            assert tescase.find('failure') is None
