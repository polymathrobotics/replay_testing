import unittest


class ReplayTestResult(unittest.TextTestResult):
    """
    Subclass of unittest.TestResult that collects more information about the tests that ran.

    This class extends TestResult by recording all of the tests that ran, and by recording
    start and stop time for the individual test cases
    """

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        self.__test_cases = {}
        super().__init__(stream, descriptions, verbosity)

    @property
    def testCases(self):
        return self.__test_cases.keys()
     
    def append(self, results):
        self.__test_cases.update(results.__test_cases)

        self.failures += results.failures
        self.errors += results.errors
        self.testsRun += results.testsRun
        self.skipped += results.skipped
        self.expectedFailures += results.expectedFailures
        self.unexpectedSuccesses += results.unexpectedSuccesses