"""
Configuration
"""

import os

import exceptions

class Config(object):
    """
    The Config class handles all configuration for pokemontools. Other classes
    and functions use a Config object to determine where expected files can be
    located.
    """

    def __init__(self, **kwargs):
        """
        Store all parameters.
        """
        self._config = {}

        for (key, value) in kwargs.items():
            if key not in self.__dict__:
                self._config[key] = value
            else:
                raise exceptions.ConfigException(
                    "Can't store \"{0}\" in configuration because the key conflicts with an existing property."
                    .format(key)
                )

        if "path" not in self._config:
            self._config["path"] = os.getcwd()

    def __getattr__(self, key):
        """
        Grab the value from the class properties, then check the configuration,
        and raise an exception if nothing works.
        """
        if key in self.__dict__:
            return self.__dict__[key]
        elif key in self._config:
            return self._config[key]
        else:
            raise exceptions.ConfigException(
                "no config found for \"{0}\"".format(key)
            )
