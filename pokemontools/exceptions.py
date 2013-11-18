"""
Custom exceptions used throughout the project.
"""

class AddressException(Exception):
    """
    There was a problem with an address. Maybe it was out of range or invalid.
    """

class TextScriptException(Exception):
    """
    TextScript encountered an inconsistency or problem.
    """

class PreprocessorException(Exception):
    """
    There was a problem in the preprocessor.
    """

class MacroException(PreprocessorException):
    """
    There was a problem with a macro.
    """
