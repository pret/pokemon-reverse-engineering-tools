#!/bin/python
# coding: utf-8

"""
Recursively scan an asm file for dependencies.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import argparse
import os.path


def scan_file(filename):
    with open(filename) as f:
        for line in f:
            if 'INC' not in line:
                continue
            line = line.split(';')[0]
            if 'INCLUDE' in line:
                include = line.split('"')[1]
                if os.path.exists("src/"):
                    yield "src/" + include
                    for inc in scan_file("src/" + include):
                        yield inc
                else:
                    yield include
                    for inc in scan_file(include):
                        yield inc
            elif 'INCBIN' in line:
                include = line.split('"')[1]
                if 'baserom.gbc' not in line and os.path.exists("src/"):
                    yield "src/" + include
                else:
                    yield include


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('filenames', nargs='*')
    args = ap.parse_args()
    includes = set()
    for filename in set(args.filenames):
        includes.update(scan_file(filename))
    sys.stdout.write(' '.join(sorted(includes)))


if __name__ == '__main__':
    main()
