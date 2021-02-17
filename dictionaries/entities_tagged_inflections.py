#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shlex
import sys

from abc import ABC, abstractmethod

class EntitiesTaggedInflections(ABC):
	def __init__(self, infile, outfile):
		self.infile = os.path.realpath(infile)
		self.outfile = os.path.realpath(outfile)
		self.outlogfile = '{}.log'.format(self.outfile)
		self.outerrfile = '{}.err.log'.format(self.outfile)
		self.outdir = os.path.dirname(self.outfile)
		if not os.path.exists(self.outdir):
			os.makedirs(os.path.exists)

	def process(self):
		cmd = shlex.split(self.getProcessCommand())
		
		with open(self.outlogfile, 'wb') as logfile, open(self.outerrfile, 'wb') as errfile:
			ps = subprocess.Popen(cmd, stdout = logfile, stderr = errfile)
			ps.communicate()


	@abstractmethod
	def getProcessCommand(self):
		raise NotImplementedError()


	def processExtra(self):
		return
