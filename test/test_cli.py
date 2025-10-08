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

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from replay_testing.cli import main

basic_replay = Path(__file__).parent / 'replay_tests' / 'basic_replay.py'


def test_cli_with_replay_test_file_argument():
    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', str(basic_replay)]

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()

    # Check that exit code is 0 (indicating success)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_cli_xml_output_success(capsys, tmp_path):
    xml_path = tmp_path / 'test.xml'

    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', str(basic_replay), '--junit-xml', str(xml_path), '--verbose']

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
