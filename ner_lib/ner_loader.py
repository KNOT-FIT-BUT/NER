#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib
import importlib.util

class NerLoader():
	@staticmethod
	def load(module, lang, initiate):
		module2import = "..lang_modules.{}.{}".format(lang, module)
		package = __name__ if '.' in __name__ else '.' + __name__

		try:
			importlib.util.find_spec(module2import, package)
		except ModuleNotFoundError:
			module2import = module

		lang_module = importlib.import_module(module2import, package)
		LangClass = getattr(lang_module, initiate)

		return LangClass(lang)
