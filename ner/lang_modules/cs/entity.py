#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from ...entity import Entity as BaseEntity



class Entity(BaseEntity):
    def apply_lang_depended_sense_rules(self):
        # only event can start with word během
        if(self.left_context(" během ")):
        	self.senses = [s for s in self.senses if self.kb.get_ent_type(s) == "event"]
