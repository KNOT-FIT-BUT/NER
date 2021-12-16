 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from namelist import Namelist as ParentClass


class Namelist(ParentClass):
	def getSaintVariants(self):
		return set([
			'Svätý', 'Svätého', 'Svätému', 'Svätom', 'Svätým',
			'Svätá', 'Svätej', 'Svätú', 'Svätou',
			'Svätí', 'Svätých', 'Svätým', 'Svätými'
		])


	def getSaintAbb(self):
		return 'Sv'


	def getLangUnwantedMatch(self):
		return set(['z', 'Princ'])
