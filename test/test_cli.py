import os
import pytest
import sys
from replay_testing.cli import main
from ament_index_python.packages import get_package_share_directory
import xml.etree.ElementTree as ET


replay_testing_dir = get_package_share_directory('replay_testing')


@pytest.mark.skip
def test_cli_with_replay_test_file_argument():
    replay_file_path = os.path.join(
        replay_testing_dir, "test", "replay_tests", "basic_replay.py")

    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', replay_file_path]

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()

    # Check that exit code is 0 (indicating success)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_cli_xml_output(capsys):
    xml_path = os.path.join("/tmp", "test.xml")
    replay_file_path = os.path.join(
        replay_testing_dir, "test", "replay_tests", "basic_replay.py")

    # Mock sys.argv for the CLI arguments
    sys.argv = ['replay_test', replay_file_path,
                "--junit-xml", xml_path, "--verbose"]

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()

    # Check that exit code is 0 (indicating success)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    junit_xml = ET.parse(xml_path)
    root = junit_xml.getroot()

    # Assert top level name
    assert root.tag == 'testsuites'

    # Assert on test suites within <testsuites> in a loop
    for testsuite in root.iter('testsuite'):
        assert testsuite.get('tests') == '1'
