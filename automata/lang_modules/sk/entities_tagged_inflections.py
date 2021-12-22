#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

import os
import shlex
import subprocess

from entities_tagged_inflections import EntitiesTaggedInflections as ParentClass


class EntitiesTaggedInflections(ParentClass):
	def getProcessCommand(self):
		dir_script = os.path.join(os.getcwd(), os.path.dirname(__file__))
		return 'python3 {}/../../libs/namegen/namegen.py --include-no-morphs --error-words {}/ma_unknown_words.lntrf -o "{}" "{}"'.format(dir_script, self.outdir, self.outfile, self.infile)


	def processExtra(self):
		for type_flag, fn_label in {'G': 'given_names', 'L': 'locations', 'S': 'surnames'}.items():
			fn_out = '{}/ma_suggested_{}.lntrf'.format(self.outdir, fn_label)
			with open(fn_out, 'wb') as fout:
				subprocess.Popen(shlex.split('grep -P "\tj{}" {}/ma_unknown_words.lntrf'.format(type_flag, self.outdir)), stdout = fout)
