# coding: utf-8

"""
Recursively scan an asm file for rgbasm INCLUDEs and INCBINs.
Used to generate dependencies for each rgbasm object.
"""

import os
import sys

import configuration
conf = configuration.Config()

def recursive_scan(filename, includes = []):
	if (filename[-4:] == '.asm' or filename[-3] == '.tx') and os.path.exists(filename):
		lines = open(filename).readlines()
		for line in lines:
			for directive in ('INCLUDE', 'INCBIN'):
				if directive in line:
					line = line[:line.find(';')]
					if directive in line:
						include = line.split('"')[1]
						if include not in includes:
							includes += [include]
							includes = recursive_scan(os.path.join(conf.path, include), includes)
						break
	return includes

if __name__ == '__main__':
	filenames = sys.argv[1:]
	dependencies = []
	for filename in filenames:
		dependencies += recursive_scan(os.path.join(conf.path, filename))
	dependencies = list(set(dependencies))
	sys.stdout.write(' '.join(dependencies))

