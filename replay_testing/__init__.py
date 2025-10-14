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

from .decorators.analyze import analyze
from .decorators.fixtures import fixtures
from .decorators.run import run
from .fixtures import BaseFixture, LocalFixture, NexusFixture, S3Fixture
from .junit_to_xml import unittest_results_to_xml
from .logging_config import get_logger
from .models import ReplayRunParams, RunnerArgs
from .reader import get_sequential_mcap_reader, read_messages
from .replay_runner import ReplayTestingRunner

# Alias for backward compatibility. Should be removed in future versions.
McapFixture = LocalFixture

__all__ = [
    'fixtures',
    'run',
    'analyze',
    'ReplayTestingRunner',
    'get_sequential_mcap_reader',
    'read_messages',
    'ReplayRunParams',
    'RunnerArgs',
    'unittest_results_to_xml',
    'get_logger',
    'BaseFixture',
    'LocalFixture',
    'McapFixture',
    'NexusFixture',
    'S3Fixture',
]
