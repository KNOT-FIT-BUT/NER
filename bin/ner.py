#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3

"""
Copyright 2014 Brno University of Technology

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# ***********************************************
# * Soubor:  ner.py                             *
# * Datum:   2020-08-31                         *
# * Autor:   Jan Doležal, idolezal@fit.vutbr.cz *
# ***********************************************

# ====== IMPORTY ======
import sys

if __package__ == "" or __package__ is None and not hasattr(sys, 'frozen'):
	# direct call of this script
	import os.path
	path = os.path.realpath(os.path.abspath(__file__))
	sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(path))))
	sys.path.append("/usr/lib/python3/dist-packages") # for debugging with debugger pudb3

import NER.ner

# ====== MAIN ======

if __name__ == "__main__":
	sys.exit(NER.ner.main())

# konec souboru ner.py
