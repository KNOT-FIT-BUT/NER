#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# <LOKÁLNÍ IMPORTY>
from ...ner_knowledge_base import KnowledgeBase as BaseKnowledgeBase
# </LOKÁLNÍ IMPORTY>

class KnowledgeBase(BaseKnowledgeBase):
	def __init__(self, lang):
		super().__init__(lang)
