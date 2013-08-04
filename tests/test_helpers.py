import sys
import inspect

import unittest

from helpers import (
    load_tests,
    check_has_test,
    assemble_test_cases,
    find_untested_methods,
    report_untested,
)

class TestMetaTesting(unittest.TestCase):
    """test whether or not i am finding at least
    some of the tests in this file"""
    tests = None

    def setUp(self):
        if self.tests == None:
            self.__class__.tests = assemble_test_cases()

    def test_assemble_test_cases_count(self):
        "does assemble_test_cases find some tests?"
        self.failUnless(len(self.tests) > 0)

    def test_assemble_test_cases_inclusion(self):
        "is this class found by assemble_test_cases?"
        # i guess it would have to be for this to be running?
        self.failUnless(self.__class__ in self.tests)

    def test_assemble_test_cases_others(self):
        "test other inclusions for assemble_test_cases"
        self.failUnless(TestRomStr in self.tests)
        self.failUnless(TestCram in self.tests)

    def test_check_has_test(self):
        self.failUnless(check_has_test("beaver", ["test_beaver"]))
        self.failUnless(check_has_test("beaver", ["test_beaver_2"]))
        self.failIf(check_has_test("beaver_1", ["test_beaver"]))

    def test_find_untested_methods(self):
        untested = find_untested_methods()
        # the return type must be an iterable
        self.failUnless(hasattr(untested, "__iter__"))
        #.. basically, a list
        self.failUnless(isinstance(untested, list))

    def test_find_untested_methods_method(self):
        """create a function and see if it is found"""
        # setup a function in the global namespace
        global some_random_test_method
        # define the method
        def some_random_test_method(): pass
        # first make sure it is in the global scope
        members = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        func_names = [functuple[0] for functuple in members]
        self.assertIn("some_random_test_method", func_names)
        # test whether or not it is found by find_untested_methods
        untested = find_untested_methods()
        self.assertIn("some_random_test_method", untested)
        # remove the test method from the global namespace
        del some_random_test_method

    def test_load_tests(self):
        loader = unittest.TestLoader()
        suite = load_tests(loader, None, None)
        suite._tests[0]._testMethodName
        membership_test = lambda member: \
            inspect.isclass(member) and issubclass(member, unittest.TestCase)
        tests = inspect.getmembers(sys.modules[__name__], membership_test)
        classes = [x[1] for x in tests]
        for test in suite._tests:
            self.assertIn(test.__class__, classes)

    def test_report_untested(self):
        untested = find_untested_methods()
        output = report_untested()
        if len(untested) > 0:
            self.assertIn("NOT TESTED", output)
            for name in untested:
                self.assertIn(name, output)
        elif len(untested) == 0:
            self.assertNotIn("NOT TESTED", output)
