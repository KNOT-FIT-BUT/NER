#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
sys.path.append("../..") 

from ...ner_knowledge_base import KnowledgeBase as BaseKnowledgeBase
from libs.utils import remove_accent

class KnowledgeBase(BaseKnowledgeBase):
	def __init__(self, lang):
		super().__init__(lang)


	def get_subnames(self, whole_names, ent_type_set, line):
		'''
		From a list of whole names for a given person, it creates a set of all possible subnames.
		For example, for the name name "George Washington", it creates a set containing two subnames - "George" and "Washington".
		'''

		forbidden = ["Pán", "Pani", "Svatý"]
		#roles = ["Baron", "Prince", "Duke", "Earl", "King", "Pope", "Queen", "Artist", "Painter"]
		regex_place = re.compile(r" (z|ze) .*")
		#regex_role = re.compile(r"[Tt]he [a-zA-Z]+")
		regex_van = re.compile(r"[Vv]an [a-zA-Z]+")
		regex_name = re.compile(r"[A-Z][a-z-']+[a-zA-Z]*[a-z]+") # this should match only a nice name
		names = set()
		roles = set()  # FIXME: Přepíše předchozí definici. Je to chyba?

		# getting roles for artists and persons
		if "person" in ent_type_set:
			for ent_supertype in ent_type_set:
				if ent_supertype != "person" and not ent_supertype.startswith("__"):
					roles.add(ent_supertype)
		#if ent_type == "artist":
		#	roles.add("artist")
		#	preferred_role = self.get_data_for(line, "PREFERRED ROLE")
		#	if preferred_role and " " not in preferred_role:
		#		roles.add(preferred_role)
		#	other_roles = self.get_data_for(line, "OTHER ROLE").split(KB_MULTIVALUE_DELIM)
		#	for other_role in other_roles:
		#		if other_role and " " not in other_role:
		#			roles.add(other_role)
#		if ent_type == "person":
#			professions = self.get_data_for(line, "JOBS").split(KB_MULTIVALUE_DELIM)
#			for profession in professions:
#				if profession:
#					roles.add(profession)
#
#		for role in roles:
#			role = role.lower()
#			names.add(role)
#			self.fragments.add(role)
#			self.fragments.add(role.decode('utf8').title())

		for whole_name in whole_names:

			# removing a part of the name with location information (e.g. " of Polestown" from the name "Richard Butler of Polestown")
			whole_name = regex_place.sub("", whole_name)

			# searching for a role
			#role = regex_role.match(whole_name)
			#if role:
			#	match = role.group()
			#	if match.split(" ")[1] in roles:
			#		names.add(match)
			#		match = match.lower()
			#		self.fragments.add(match)
			#		self.fragments.add(match.title())
			#		self.fragments.add(match.replace("the", "The"))

			# splitting the name to the parts
			subnames = whole_name.split(' ')
			#print(whole_name)
			for subname in subnames:
				if subname.endswith(","):
					subname = subname[:-1]
				# removing accent, because python re module doesn't support [A-Z] for Unicode
				subname_without_accent = remove_accent(subname)
				result = regex_name.match(subname_without_accent)
				if result:
					match = result.group()
					if match == subname_without_accent and subname not in forbidden and match not in roles:
						names.add(subname)
						self.fragments.add(subname)
						self.fragments.add(subname_without_accent)

			# searching for "van Eyck"
			vanName = regex_van.search(whole_name)
			if vanName:
				match = vanName.group()
				names.add(match)
				match = "v" + match[1:]
				self.fragments.add(match)
				self.fragments.add(match.replace("van", "Van"))
				self.fragments.add(remove_accent(match))
				self.fragments.add(remove_accent(match.replace("van", "Van")))

		return names
