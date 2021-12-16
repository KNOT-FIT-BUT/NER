#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ...nationalities import Nationalities as BaseNationalities

class Nationalities(BaseNationalities):
	def __init__(self, lang):
		super().__init__(lang)


	def get_jurisdictions(self):
		jurisdictions = []

		for jur_female in self.get_nationalities():
			jur_male = jur_female[:-1] + ("ý" if jur_female[-1:] == "á" else "y")
			jur_middle = jur_female[:-1] + ("é" if jur_female[-1:] == "á" else "e")
			jurisdictions.append(jur_male)
			jurisdictions.append(jur_female)
			jurisdictions.append(jur_middle)

		return jurisdictions
