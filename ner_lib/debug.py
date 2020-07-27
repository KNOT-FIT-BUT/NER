#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# **************************************************
# * File:    debug.py                              *
# * Authors:                                       *
# *     Jan Doležal, xdolez52@stud.fit.vutbr.cz    *
# *     Tomáš Volf, ivolf@fit.vutbr.cz             *
# **************************************************

import sys

# For debugging:
import inspect
import traceback
import time
DEBUG_EN = True



def getInspectInfo(iContext):
	callerframerecord = inspect.stack()[iContext]
	frame = callerframerecord[0]
	info = inspect.getframeinfo(frame)
	
	return "(%s, %s, %s, time=%r, cpuTime=%r)" % (info.filename, info.function, info.lineno, time.time(), time.clock())


def print_dbg_en(*args, **kwargs):
	delim = kwargs.get("delim", " ")
	stack_num = kwargs.get("stack_num", 1)

	sys.stderr.write("%s:\n'''\n%s\n'''\n" % (getInspectInfo(stack_num), delim.join(args)))
	sys.stderr.flush()


def print_dbg(*args, **kwargs):
	if not DEBUG_EN:
		return
	if "stack_num" not in kwargs:
		kwargs["stack_num"] = 2
	print_dbg_en(*args, **kwargs)


def cur_inspect():
	return getInspectInfo(1)


def caller_inspect():
	return getInspectInfo(2)


def cur_traceback():
	formated_traceback = traceback.format_stack()[:-1]
	return "".join(formated_traceback)
