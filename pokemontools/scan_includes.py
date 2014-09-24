#!/bin/python
# coding: utf-8

"""
Recursively scan an asm file for dependencies.
"""

import os
import sys
import argparse


class IncludeReader:
	"""
	Usage:
		includer = IncludeReader()
		includer.read(filename)
	or
		includer = IncludeReader(filename='filename.asm')
		includer.read()
	"""
	path = ''
	includes = []
	directives = ['INCLUDE', 'INCBIN']
	extensions = ['.asm', '.tx']

	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

	def read(self, filename=None):
		"""
		Recursively look for includes in <filename> and add them to self.includes.
		"""
		if filename is None:
			if hasattr(self, 'filename'):
				filename = os.path.join(self.path, self.filename)
			else:
				raise Exception, 'no filename given!'
		if os.path.splitext(filename)[1] in self.extensions and os.path.exists(filename):
			for line in open(filename).readlines():
				self.read_line(line)

	def read_line(self, line):
		"""
		Add any includes in <line> to self.includes, and look for includes in those.
		"""
		parts = line[:line.find(';')].split()
		for directive in self.directives:
			if directive in map(str.upper, parts):
				include = os.path.join(self.path, parts[parts.index(directive) + 1].split('"')[1])
				if include not in self.includes:
					self.includes.append(include)
					self.read(include)

if __name__ == '__main__':
	ap = argparse.ArgumentParser()
	ap.add_argument('-i', default='')
	ap.add_argument('filenames', nargs='*')
	args = ap.parse_args()

	includes = IncludeReader(path=args.i)
	for filename in args.filenames:
		includes.read(filename)
	sys.stdout.write(' '.join(includes.includes))

