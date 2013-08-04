# -*- coding: utf-8 -*-

import sys
import inspect

import unittest

def assemble_test_cases():
    """finds classes that inherit from unittest.TestCase
    because i am too lazy to remember to add them to a
    global list of tests for the suite runner"""
    classes = []
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for (name, some_class) in clsmembers:
        if issubclass(some_class, unittest.TestCase):
            classes.append(some_class)
    return classes

def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for test_class in assemble_test_cases():
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite

def check_has_test(func_name, tested_names):
    """checks if there is a test dedicated to this function"""
    if "test_"+func_name in tested_names:
        return True
    for name in tested_names:
        if "test_"+func_name in name:
            return True
    return False

def find_untested_methods():
    """finds all untested functions in this module
    by searching for method names in test case
    method names."""
    untested = []
    avoid_funcs = ["main", "run_tests", "run_main", "copy", "deepcopy"]
    test_funcs = []
    # get a list of all classes in this module
    classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    # for each class..
    for (name, klass) in classes:
        # only look at those that have tests
        if issubclass(klass, unittest.TestCase):
            # look at this class' methods
            funcs = inspect.getmembers(klass, inspect.ismethod)
            # for each method..
            for (name2, func) in funcs:
                # store the ones that begin with test_
                if "test_" in name2 and name2[0:5] == "test_":
                    test_funcs.append([name2, func])
    # assemble a list of all test method names (test_x, test_y, ..)
    tested_names = [funcz[0] for funcz in test_funcs]
    # now get a list of all functions in this module
    funcs = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    # for each function..
    for (name, func) in funcs:
        # we don't care about some of these
        if name in avoid_funcs: continue
        # skip functions beginning with _
        if name[0] == "_": continue
        # check if this function has a test named after it
        has_test = check_has_test(name, tested_names)
        if not has_test:
            untested.append(name)
    return untested

def report_untested():
    """
    This reports about untested functions in the global namespace. This was
    originally in the crystal module, where it would list out the majority of
    the functions. Maybe it should be moved back.
    """
    untested = find_untested_methods()
    output = "NOT TESTED: ["
    first = True
    for name in untested:
        if first:
            output += name
            first = False
        else: output += ", "+name
    output += "]\n"
    output += "total untested: " + str(len(untested))
    return output
