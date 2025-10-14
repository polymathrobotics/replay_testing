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

from ..fixtures import BaseFixture
from ..logging_config import get_logger
from ..models import Mcap, ReplayTestingPhase

_logger_ = get_logger()


class fixtures:
    """Base decorator to tag a class as part of the fixtures phase."""

    def __init__(self, *args, **kwargs):
        # If args/kwargs are provided, treat them as parameters
        self.fixture_list = kwargs.get('fixture_list', None)

    def validate_class_variable(self, cls, prop: str, deprecated_variable: str):
        if hasattr(cls, deprecated_variable):
            _logger_.warning(f"Class {cls.__name__} '{prop}' attribute is deprecated. See docs for updated usage.")
            return

        if not hasattr(cls, prop):
            raise TypeError(f"Class {cls.__name__} must define a '{prop}' attribute.")

        if not isinstance(getattr(cls, prop), list):
            raise TypeError(f"Class {cls.__name} '{prop}' attribute must be a list.")

        if not all(isinstance(topic, str) for topic in getattr(cls, prop)):
            raise TypeError(f"Class {cls.__name} '{prop}' attribute must be a list of strings.")

    def __call__(self, cls):
        self.validate_class_variable(cls, 'required_input_topics', 'input_topics')
        self.validate_class_variable(cls, 'expected_output_topics', 'output_topics')

        cls.fixture_list = self.fixture_list
        cls.__annotations__['replay_testing_phase'] = ReplayTestingPhase.FIXTURES
        return cls

    @staticmethod
    def parameterize(fixture_list: list[Mcap | BaseFixture]):
        return fixtures(fixture_list=fixture_list)
