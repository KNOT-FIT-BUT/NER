#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

LANGS_ALLOWED = set(['cs'])
LANGS_MAP = {'cz': 'cs'}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIRPATH_KB_DAEMON = os.path.abspath(os.path.join(SCRIPT_DIR, "../SharedKB/var2"))
PATH_KB_DAEMON = os.path.abspath(os.path.join(DIRPATH_KB_DAEMON, "decipherKB-daemon"))
PATH_KB = os.path.abspath(os.path.join(SCRIPT_DIR, "inputs/KB.tsv"))

KB_MULTIVALUE_DELIM = "|"


def update_globals(kbd_dir, kb_path, kb_delim = '|', timeout_s = 300, timeout_e = 10):
	global DIRPATH_KB_DAEMON, PATH_KB_DAEMON, PATH_KB, KB_MULTIVALUE_DELIM, Timeout_SharedKB_start, Timeout_process_exists
	DIRPATH_KB_DAEMON = kbd_dir
	PATH_KB_DAEMON = os.path.join(DIRPATH_KB_DAEMON, "decipherKB-daemon")
	PATH_KB = kb_path 
