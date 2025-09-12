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

import inspect

from ..models import ReplayRunParams, ReplayTestingPhase


class run:
    """Decorator to mark a class or function as part of the run phase, optionally parameterized."""

    def __init__(self, *args, **kwargs):
        # If args/kwargs are provided, treat them as parameters
        self.parameters = kwargs.get('parameters', None)

    def __call__(self, cls):
        if not hasattr(cls, 'generate_launch_description'):
            raise TypeError(f"Class {cls.__name__} must define a 'generate_launch_description' method.")

        original_method = cls.generate_launch_description

        def wrapped_generate_launch_description(self, parameters):
            # Inspect the original method to see if it accepts `param`
            sig = inspect.signature(original_method)
            if len(sig.parameters) == 2:
                return original_method(self, parameters)
            else:
                return original_method(self)

        cls.generate_launch_description = wrapped_generate_launch_description
        # Attach parameters if they exist
        if self.parameters is not None:
            cls.parameters = self.parameters
        cls.__annotations__['replay_testing_phase'] = ReplayTestingPhase.RUN
        return cls

    @staticmethod
    def parameterize(parameters: list[ReplayRunParams]):
        """Decorate with parameters."""
        return run(parameters=parameters)

    @staticmethod
    def default(params: dict = {}):
        return run(parameters=[ReplayRunParams(name='default', params=params)])
