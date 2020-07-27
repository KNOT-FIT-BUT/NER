#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

LANGS_ALLOWED = set(['en', 'cz'])

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS_DIR = os.path.dirname(os.path.join(SCRIPT_DIR, "inputs"))
DIRPATH_KB_DAEMON = os.path.abspath(os.path.join(SCRIPT_DIR, "../SharedKB/var2"))
PATH_KB_DAEMON = os.path.abspath(os.path.join(DIRPATH_KB_DAEMON, "decipherKB-daemon"))

KB_MULTIVALUE_DELIM = "|"


def update_globals(kbd_dir, inputs_dir, kb_delim = '|', timeout_s = 300, timeout_e = 10):
	global DIRPATH_KB_DAEMON, PATH_KB_DAEMON, INPUTS_DIR, KB_MULTIVALUE_DELIM, Timeout_SharedKB_start, Timeout_process_exists
	DIRPATH_KB_DAEMON = kbd_dir
	PATH_KB_DAEMON = os.path.join(DIRPATH_KB_DAEMON, "decipherKB-daemon")
	INPUTS_DIR = inputs_dir 
