#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import importlib
import importlib.util
import inspect

class ModuleLoader():
	@staticmethod
	def load(module, lang, initiate, package = None):
		module2import = "lang_modules.{}.{}".format(lang, module)
		if not package:
			package = __name__ if '.' in __name__ else '.' + __name__

		spec = importlib.util.find_spec(module2import, package)
		if not spec:
			module2import = module

		lang_module = importlib.import_module(module2import, package)
		LangClass = getattr(lang_module, initiate)

		return LangClass(lang)
