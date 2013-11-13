"""
Access to data files.
"""

# hide the os import
import os as _os

# path to where these files are located
path = _os.path.abspath(_os.path.dirname(__file__))

def join(filename, path=path):
    """
    Construct the absolute path to the file.
    """
    return _os.path.join(path, filename)
