 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from namelist import Namelist as ParentClass


class Namelist(ParentClass):
	def getSaintVariants(self):
		return set([
			'Saint', 'Holy'
		])


	def getSaintAbb(self):
		return 'St'


	def getLangUnwantedMatch(self):
		return set(['from', 'Prince'])
