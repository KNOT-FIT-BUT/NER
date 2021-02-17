#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=4 softtabstop=4 noexpandtab shiftwidth=4

import os, sys
import inspect
import subprocess
import tempfile
import time

from .configs import *
# Pro debugování:
from libs.debug import print_dbg, print_dbg_en

# # Timeouty v sekundách:
Timeout_SharedKB_start = 300
Timeout_process_exists = 10

class KbDaemon(object):
	def __init__(self, kb_shm_name=None):
		self.ps = None
		self.stdout = tempfile.TemporaryFile()
		self.stderr = tempfile.TemporaryFile()
		self.exitcode = None
		self.kb_shm_name = kb_shm_name

	def start(self):
		if self.kb_shm_name:
			self.ps = subprocess.Popen([PATH_KB_DAEMON, "-s", self.kb_shm_name, PATH_KB], stdout=self.stdout, stderr=self.stderr)
		else:
			self.ps = subprocess.Popen([PATH_KB_DAEMON, PATH_KB], stdout=self.stdout, stderr=self.stderr)

		output = ""
		try:
			i = 0

			output = self.stdout.readline().decode()

			while (output == "" or output[-1] != "\n") and self.ps.poll() == None:
				if i >= Timeout_SharedKB_start:
					raise RuntimeError("Timeout of subprocess \"%s\"." % (PATH_KB_DAEMON))
				time.sleep(1)
				self.stdout.seek(0)
				output = self.stdout.readline().decode()
		except:
			self.ps.terminate()
			self.ps.wait()
			raise

		print_dbg(output)

		if (self.ps.poll() != None):
			self.onEndLogs()
			raise RuntimeError("\"%s\" has failed to start." % (PATH_KB_DAEMON))


	def stop(self):
		if not self.ps:
			return
		self.ps.terminate()

		self.onEndLogs()


	def onEndLogs(self):
		is_stop = False
		if inspect.stack()[1][3] == 'stop':
			is_stop = True

		ps_exitcode = self.ps.wait()

		self.stdout.seek(0)
		if is_stop:
			self.stdout.readline()
		self.stderr.seek(0)
		ps_stdout = self.stdout.read()
		ps_stderr = self.stderr.read()

		if (not is_stop or ps_exitcode != 0):
			sys.stderr.write("%s [EXITCODE]:\n%s\n" % (PATH_KB_DAEMON, ps_exitcode))
		if (ps_stdout):
			sys.stderr.write("%s [STDOUT]:\n%s\n" % (PATH_KB_DAEMON, ps_stdout))
		if (ps_stderr):
			sys.stderr.write("%s [STDERR]:\n%s\n" % (PATH_KB_DAEMON, ps_stderr))

		self.stdout.close()
		self.stderr.close()
		self.ps = None
		self.exitcode = ps_exitcode



class TimeoutError(Exception):
	pass



def exec_function(func, args=(), kwargs={}, timeout_duration=10, default=None):
	'''
	This function will spawn a thread and run the given function
	using the args, kwargs and return the given default value if the
	timeout_duration is exceeded.
	'''

	class InterruptableThread(threading.Thread):
		def __init__(self):
			threading.Thread.__init__(self)
			self.result = default
		def run(self):
			self.result = func(*args, **kwargs)
	it = InterruptableThread()
	it.start()
	it.join(timeout_duration)
	if it.isAlive():
		return it.result
	else:
		return it.result


def subprocess_read(ps, ps_output_stream, timeout=None):
	'''
	ps - subproces
	ps_output_stream - výstupní stream subprocesu
	timeout - maximální doba čtení [sekundy]
	'''

	if (ps.poll() != None):
		raise Exception("Internal Error: " + cur_inspect())

	result = exec_function(ps_output_stream.read, timeout_duration=timeout)
	if (result == None):
		ps.terminate()
		ps.wait()
		raise TimeoutError

	return result


def subprocess_readline(ps, ps_output_stream, timeout=None):
	'''
	ps - subproces
	ps_output_stream - výstupní stream subprocesu
	timeout - maximální doba čtení [sekundy]
	'''

	if (ps.poll() != None):
		raise Exception("Internal Error: " + cur_inspect())

	result = exec_function(ps_output_stream.readline, timeout_duration=timeout)
	if (result == None):
		ps.terminate()
		ps.wait()
		raise TimeoutError

	return result


def process_exists(proc, id = False):
	'''
	proc       -> name/id of the process
	id = True  -> search for pid
	id = False -> search for name by regex (default)
	'''

	CMD = "ps -e -o pid= -o cmd="

	ps = subprocess.Popen(CMD, shell=True, stdout=subprocess.PIPE)
	try:
		output = subprocess_read(ps, ps.stdout, timeout=Timeout_process_exists)
	except TimeoutError:
		raise RuntimeError("Timeout of subprocess \"" + CMD + "\".")
	ps.stdout.close()
	ps.wait()

	for line in output.split("\n"):
		if line != "" and line != None:
			fields = line.split()
			pid = fields[0]
			pname = fields[1]

		if (not id):
			if re.search("^(?:.*/)?" + proc + "(?:\s+.*)?$", pname):
				return True
		else:
			if (proc == pid):
				return True
	return False


def KB_is_running():
	if process_exists(os.path.basename(PATH_KB_DAEMON)):
		return True
	return False
