import unittest


class ReplayTestResult(unittest.TextTestResult):
    """
    Subclass of unittest.TestResult that collects more information about the tests that ran.

    This class extends TestResult by recording all of the tests that ran, and by recording
    start and stop time for the individual test cases
    """

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        if verbosity is None:
            verbosity = 1  # Default verbosity level if not provided
        self.successes = []
        super().__init__(stream, descriptions, verbosity)

    def addSuccess(self, test):
        self.successes.append(test)
