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

from ..models import ReplayTestingPhase, McapFixture


class fixtures:
    """Base decorator to tag a class as part of the fixtures phase."""

    def __init__(self, *args, **kwargs):
        # If args/kwargs are provided, treat them as parameters
        self.fixture_list = kwargs.get("fixture_list", None)

    def __call__(self, cls):
        if not hasattr(cls, "input_topics"):
            raise TypeError(f"Class {cls.__name__} must define a 'input_topics' attribute.")

        if not isinstance(cls.input_topics, list):
            raise TypeError(f"Class {cls.__name} 'input_topics' attribute must be a list.")

        if not all(isinstance(topic, str) for topic in cls.input_topics):
            raise TypeError(
                f"Class {cls.__name} 'input_topics' attribute must be a list of strings."
            )

        if not hasattr(cls, "output_topics"):
            raise TypeError(f"Class {cls.__name__} must define a 'output_topics' attribute.")

        if not isinstance(cls.output_topics, list):
            raise TypeError(f"Class {cls.__name} 'output_topics' attribute must be a list.")

        if not all(isinstance(topic, str) for topic in cls.output_topics):
            raise TypeError(
                f"Class {cls.__name} 'input_topics' attribute must be a list of strings."
            )

        cls.fixture_list = self.fixture_list
        cls.__annotations__["replay_testing_phase"] = ReplayTestingPhase.FIXTURES
        return cls

    @staticmethod
    def parameterize(fixture_list: list[McapFixture]):
        return fixtures(fixture_list=fixture_list)
