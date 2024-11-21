#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import importlib
import importlib.util

class NatLoader():
	@staticmethod
	def load(lang):
		module = "..lang_modules.{}.nationalities".format(lang)
		package = __name__ if '.' in __name__ else '.' + __name__

		try:
			spec = importlib.util.find_spec(module, package)
		except ModuleNotFoundError:
			module = "..nationalities"

		lang_module = importlib.import_module(module, package)
		LangClass = getattr(lang_module, "Nationalities")
		res = LangClass(lang)

		return res
