#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import importlib

class LibsLoader():

	def load(self, lang):
		module = "{}.nationalities".format(lang)
		if not os.path.exists(module):
			module = "nationalities"
		lang_module = importlib.import_module(module)
		LangClass = getattr(lang_module, "Nationalities")
		return LangClass() 
