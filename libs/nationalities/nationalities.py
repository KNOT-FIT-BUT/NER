#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
import os
import sys

class Nationalities():
	def __init__(self, lang):
		self.lang = lang
		try:
			with open("{}/data/{}.txt".format(os.path.dirname(__file__), self.lang)) as f:
				self.nationalities = f.read().splitlines()
		except IOError:
			print("Nationality input data file for language \"{}\" not found or is not accessible.".format(self.lang), file = sys.stderr, flush = True)
			sys.exit(errno.EIO)

	def get_nationalities(self):
		nationalities = []
		
		for nat in self.nationalities:
			nationalities.append(nat)
			nationalities.append(nat.lower())
		
		return nationalities

	def get_jurisdictions(self):
		return self.get_nationalities()
