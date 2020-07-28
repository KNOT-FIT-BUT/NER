#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ...entity import Entity as BaseEntity

class Entity(BaseEntity):
    def apply_lang_depended_sense_rules(self):
        # locations cannot end with 's
        self.senses = [s for s in self.senses if not (("location" in self.kb.get_ent_type(s) or "locations" in self.kb.get_ent_type(s)) and self.right_context("'s"))]

        # locations cannot start with The
        self.senses = [s for s in self.senses if not ("location" in self.kb.get_ent_type(s) and self.source.startswith("The "))]

        # only locations can have preposition "into"
        self.senses = [s for s in self.senses if not ("location" not in self.kb.get_ent_type(s) and self.left_context(" into "))] # NOTE: Můžeme se na to spolehnout?


    def is_location_coreference(self):
        if self.source == "There" and (self.right_context(" is ") or self.right_context(" are ") or self.right_context(" was ") or self.right_context(" were ") or self.right_context(" has ") or self.right_context(" have ") or self.right_context(" had ")):
            return True
