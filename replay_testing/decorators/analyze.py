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

    WrappedAnalyze.__annotations__["replay_testing_phase"] = (
        ReplayTestingPhase.ANALYZE
    )
    WrappedAnalyze.__annotations__["suite_name"] = cls.__name__
 
    return WrappedAnalyze
