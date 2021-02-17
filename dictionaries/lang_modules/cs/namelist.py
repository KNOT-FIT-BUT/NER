 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from namelist import Namelist as ParentClass


class Namelist(ParentClass):
	def getSaintVariants(self):
		return set([
			'Svatý', 'Svatého', 'Svatému', 'Svatém', 'Svatým',
			'Svatá', 'Svaté', 'Svatou',
			'Svatí', 'Svatých', 'Svatým', 'Svatými'
		])


	def getSaintAbb(self):
		return 'Sv'


	def getLangUnwantedMatch(self):
		return set(['z', 'Princ'])
