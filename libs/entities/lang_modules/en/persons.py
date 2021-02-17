#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Author: Tomáš Volf, ivolf[at]fit.vutbr.cz

from ...persons import Persons as BasePersons

class Persons(BasePersons):
	def get_FORBIDDEN_NAMES(self):
		return ["Mr", "Sir", "Sr", "Jr", "The", "St", "University", "Saint"]
#	ROLE_PREFIX = "the"
