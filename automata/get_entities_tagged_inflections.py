#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import importlib
import importlib.util
import sys


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-l', '--lang', type = str, required = True, help = 'Language to process.')
	parser.add_argument('-i', '--input', type = str, required = True, help = 'Input file with entities (output of get_entites_with_typeflags.py).')
	parser.add_argument('-o', '--output', type = str, required = True, help = 'Output file with tagged and inflected entities.')
	args = parser.parse_args()


	module2import = 'lang_modules.{}.entities_tagged_inflections'.format(args.lang)

	try:
		module_eti = importlib.import_module(module2import)
	except ModuleNotFoundError as e:
		print(f"ERROR in tagged inflections for entities: No implementation for given language. (Detail: {e})", flush = True, file = sys.stderr)
		sys.exit(1)

	module_eti = importlib.import_module(module2import)
	eti = module_eti.EntitiesTaggedInflections(args.input, args.output)
	eti.process()
