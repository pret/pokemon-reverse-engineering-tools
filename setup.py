#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# for uploading to pypi
if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

# There's some intersection with requirements.txt but pypi can't handle git
# dependencies.
requires = [
    "mock",
    "nose",
    "vba_wrapper==0.0.2",
]

setup(
    name="pokemontools",
    version="1.6.0",
    description="Tools for compiling and disassembling Pokémon Red and Pokémon Crystal.",
    long_description=open("README.md", "r").read(),
    license="BSD",
    author="Bryan Bishop",
    author_email="kanzure@gmail.com",
    url="https://github.com/kanzure/pokemon-reverse-engineering-tools",
    packages=["pokemontools", "redtools"],
    package_dir={"pokemontools": "pokemontools", "redtools": "redtools"},
    include_package_data=True,
    install_requires=requires,
    platforms="any",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
    ]
)
