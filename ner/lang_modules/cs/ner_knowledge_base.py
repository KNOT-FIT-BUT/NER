#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append("../..") 

from ...ner_knowledge_base import KnowledgeBase as BaseKnowledgeBase

class KnowledgeBase(BaseKnowledgeBase):
	def __init__(self, lang):
		super().__init__(lang)
