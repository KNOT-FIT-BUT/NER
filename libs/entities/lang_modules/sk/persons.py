#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Author: Tomáš Volf, ivolf[at]fit.vutbr.cz

import sys
sys.path.append('../..')

from ...persons import Persons as BasePersons


class Persons(BasePersons):
	def get_FORBIDDEN_NAMES(self):
		return ["pán", "pan", "paní", "pani", "p.", "svätý", "svätá", "sv."]

	def get_LOCATION_PREPOSITIONS(self):
		return super().get_LOCATION_PREPOSITIONS() + ["z", "zo"]

	def get_LOCATION_PREPOSITIONS_CONJUNCTIONS(self):
		return super().get_LOCATION_PREPOSITIONS_CONJUNCTIONS() + ["a"]
