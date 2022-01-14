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

	def process(self) -> None:
		process_command = self.getProcessCommand()
		if process_command:
			process_command.split()[0]
			with open(self.outlogfile, 'wb') as f_log, open(self.outerrfile, 'wb') as f_err:
				ps = subprocess.Popen(shlex.split(process_command), stdout=f_log, stderr=f_err)
				ps.communicate()
				retcode = ps.returncode
				if retcode == 2:
					with open(self.outerrfile, 'r') as f_tmp:
						for ferr_lastline in f_tmp:
							pass
					print(f"ERROR in tagged inflections of entities: Bad filepath of executable - failed with return code {retcode}.\nDetail: {ferr_lastline.strip()}.\n(command: {process_command})", file=sys.stderr)
					sys.exit(10)
				elif retcode:
					print(f"ERROR in tagged inflections of entities: Execution of following command failed with return code {retcode}. For details see error log in {self.outerrfile}.\n(command: {process_command})", file=sys.stderr)
					sys.exit(10)
			self.processExtra()


	@abstractmethod
	def getProcessCommand(self) -> str:
		raise NotImplementedError()


	def processExtra(self) -> None:
		self._process_extra_namegen()

	def _process_namegen(self) -> str:
		dir_script = os.path.join(os.getcwd(), os.path.dirname(__file__))
		return 'python3 {}/../libs/namegen/namegen.py --include-no-morphs --error-words {}/ma_unknown_words.lntrf -o "{}" "{}"'.format(dir_script, self.outdir, self.outfile, self.infile)

	def _process_extra_namegen(self) -> None:
		for type_flag, fn_label in {'G': 'given_names', 'L': 'locations', 'S': 'surnames'}.items():
			fn_out = f"{self.outdir}/ma_suggested_{fn_label}.lntrf"
			cmd = f'grep -P "\tj{type_flag}" {self.outdir}/ma_unknown_words.lntrf'
			with open(fn_out, 'w') as f_out:
				try:
					out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT, universal_newlines=True)
				except subprocess.CalledProcessError as e:
					err_detail = ""
					if e.returncode == 2:
						err_msg_base = "File not found:"
					elif e.returncode:
						err_msg_base = "Execution of following command"
					print(f"ERROR in name suggestions: {err_msg_base} failed with return code {e.returncode}.\nDetail: {e.output.strip().splitlines()[-1]}\n(command: {cmd})", file=sys.stderr)
					sys.exit(11)
				else:
					f_out.write(out)

