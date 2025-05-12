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

import unittest

from ..models import ReplayTestingPhase


def analyze(cls):
    # Create a wrapper class that inherits from unittest.TestCase
    class WrappedAnalyze(cls, unittest.TestCase):
        def __init__(self, *args, **kwargs):
            # Initialize TestCase using super()
            super().__init__(*args, **kwargs)

            # Only call cls.__init__ if it is user-defined (not the default object.__init__)
            if cls.__init__ is not object.__init__:
                cls.__init__(self, *args, **kwargs)

    WrappedAnalyze.__annotations__['replay_testing_phase'] = ReplayTestingPhase.ANALYZE
    WrappedAnalyze.__annotations__['suite_name'] = cls.__name__

    return WrappedAnalyze
