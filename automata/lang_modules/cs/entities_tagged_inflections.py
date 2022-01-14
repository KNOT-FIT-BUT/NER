#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

import os
import shlex
import subprocess

from entities_tagged_inflections import EntitiesTaggedInflections as ParentClass


class EntitiesTaggedInflections(ParentClass):
	def getProcessCommand(self) -> str:
		return self._process_namegen()
