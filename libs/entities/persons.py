#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Author: Tomáš Volf, ivolf[at]fit.vutbr.cz

import regex
import libs.re_utils as re_utils
from abc import ABC
from libs.automata_variants import AutomataVariants
from libs.utils import remove_accent


class Persons(ABC):
	# Common name preposition for all languages - it should not be completed or overriden in lang-specific modules
	NAME_PREPOSITIONS = ["van der", "van", # Dutch / Flemish
					     "von", "zu",      # Germany
					     "de", "du",       # French
					     "da",             # Italian or Portuguese
					     "di",             # Italian or Spanish
					     "dalla", "del", "dos", "el", "la", "le", "ben", "bin", "y", # http://prirucka.ujc.cas.cz/?id=326
						]
    # Common name prefixes for all languages - it should not be completed or overriden in lang-specific modules
	NAME_PREFIXES = ["d'", "o'"]             # French / Italian / Portuguese / Spanish

	# overriden in lang-specific modules
	def get_FORBIDDEN_NAMES(self):
		return []

	# overriden in lang-specific modules
	def get_ROLE_PREFIX(self):
		return None
    
	# it may be completed or overriden in lang-specific modules
	def get_LOCATION_PREPOSITIONS(self):
		return ["of"]

	# it may be completed or overriden in lang-specific modules
	def get_LOCATION_PREPOSITIONS_CONJUNCTIONS(self):
		return ["and"]


	def __init__(self, lang):
		self.lang = lang


	def get_normalized_subnames(self, src_names, roles = [], separate_to_names = False, config = AutomataVariants.DEFAULT):
		'''
		From a list of surnames for a given person, it creates a set of all possible surnames variants respecting settings of lowercase / non-accent / ..
		For example:
		   * ["Havel"] => ["Havel"]
		   * ["O'Connor"] => ["O'Connor", "o'Connor", "Connor"]
		   * ["van Beethoven"] => ["Ludwig", "Beethoven", "van Beethoven", "Van Beethoven"]
		'''

		if AutomataVariants.isLowercase(config):
			regex_flags = regex.IGNORECASE
		else:
			regex_flags = 0

		# tmp_preposition in the form of "([Vv]an|[Zz]u|..)"
		# Warning: contain space on the beginning to avoid match "Ivan Novák" as "van Novák" => it is needed to get substring from second char
		tmp_prepositions = re_utils.list2FirstIncaseAlternation(self.NAME_PREPOSITIONS)
		regex_prepositions_remove = regex.compile(r" {} ".format(tmp_prepositions))
		regex_prepositions_name = regex.compile(r" {} \p{{Lu}}\p{{L}}+".format(tmp_prepositions), flags=regex_flags)

		# tmp_prefixes in the form og "([Dd]\\'|[Oo]\\'|..)"
		tmp_prefixes = re_utils.list2FirstIncaseAlternation(self.NAME_PREFIXES)
		regex_prefixes_only_check = regex.compile(r"^{}\p{{Lu}}".format(tmp_prefixes), flags=regex_flags)
		regex_prefixes_only = regex.compile(r"^{}".format(tmp_prefixes))

		str_regex_location_remove = r" (?:{}) .*".format("|".join(map(regex.escape, self.get_LOCATION_PREPOSITIONS())))
		regex_location_remove = regex.compile(str_regex_location_remove, flags=regex_flags)
		regex_name = regex.compile(r"^( ?(?:{})?\p{{Lu}}(\p{{L}}+)?(['-]\p{{Lu}}\p{{L}}+)*)+(?:{})?$".format(tmp_prefixes, str_regex_location_remove), flags=regex_flags) # this should match only a nice name (must support prefixes)
#		regex_name = regex.compile(r"({})?[A-Z][a-z-']+[a-zA-Z]*[a-z]+".format(tmp_prefixes)) # this should match only a nice name (must support prefixes)

		regex_subname_location = regex.compile(r"([^ ]+" + str_regex_location_remove + r")")
		regex_role = None

		if self.get_ROLE_PREFIX():
			regex_role_prefix = regex.escape(self.get_ROLE_PREFIX().lower())
			regex_role = regex.compile(r"[{}{}]{} \p{{L}}+".format(regex_role_prefix[0], regex_role_prefix[0].upper(), regex_role_prefix[1:]))

		roles_lower = set()
		for role in roles:
			roles_lower.add(role.lower())

		names = set()

		for name in src_names:
			# remove all name flags
			name = regex.sub(r"#lang=[^#|]*", "", name)
            
			# normalize whitespaces
			name = regex.sub('\s+', ' ', name)
			name_with_location = name
			subname_location = regex_subname_location.search(name)
			if subname_location:
				subname_location = subname_location.group()

			# remove a part of the name with location information (e.g. " of Polestown" from the name "Richard Butler of Polestown")
			name = regex_location_remove.sub("", name)
			if name.upper() != name:
				name = name.title()

			if separate_to_names:
				# split the name only (without prepositions) to the parts
				subnames = regex_prepositions_remove.sub(" ", name).split()
			else:
				subnames = [name]

			if not separate_to_names:
				subnames.append(name_with_location)
			if subname_location and subname_location != name_with_location:
				# Name part without location
				subnames.append(subname_location)

			# searching for a role
			if regex_role:
				role = regex_role.match(name)
				if role:
					match = role.group()
					role_itself = match.split(" ")[1 if self.get_ROLE_PREFIX() else 0]
					if role_itself.lower() not in roles_lower:
						names.add(match) # For case, that role has specific capitalization
						roles_lower.append(role_itself.lower())

			for subname in subnames:
				if not len(subname):
					continue
				if subname[-1] == ",":
					subname = subname[:-1]

				subname_lower = subname.lower()

				# skip invalid / forbidden names
				if subname_lower not in self.get_FORBIDDEN_NAMES() or subname_lower not in roles_lower:
					# normalize name to start with capital, including name with prefix (for example o'... => O'...)
					subname = subname[0].upper() + subname[1:]
					# remove accent, because python re module doesn't support [A-Z] for Unicode
					subname_without_accent = remove_accent(subname)
					result = regex_name.match(subname)
					if result:
						# add non-accent variant (if required) to processing (only if not same as base name)
						for subname in [subname, subname_without_accent] if (AutomataVariants.isNonaccent(config) and subname != subname_without_accent) else [subname]:
							if (AutomataVariants.isLowercase(config)):
								subname = subname.lower()
							names.add(subname)
							if regex.match(regex_prefixes_only_check, subname):
								# add also a variant with small letter starting prefix => "o'Conor"
								if (not subname[0].islower()):
									names.add(subname[0].lower() + subname[1:])

								# from "O'Connor" add also surname only without prefix => "Connor"
								nonprefix = regex_prefixes_only.sub('', subname)
								names.add(nonprefix.lower() if AutomataVariants.isLowercase(config) else nonprefix.capitalize())

			# search for names with preposition, i.e. "van Eyck"
			preposition_name = regex_prepositions_name.search(name.title())
			if preposition_name:
				match = preposition_name.group()

				# normalize name to start with capital, including name with preposition (for example "van Eyck" => "Van Eyck")
				# Warning: contain space on the beginning to avoid match "Ivan Novák" as "van Novák" => it is needed to get substring from second char
				subname = match[1:].title()
				subname_without_accent = remove_accent(subname)

				# add non-accent variant (if required) to processing (only if not same as base name)
				for subname in [subname, subname_without_accent] if (AutomataVariants.isNonaccent(config) and subname != subname_without_accent) else [subname]:
					if (AutomataVariants.isLowercase(config)):
						subname = subname.lower()
					names.add(subname)

					# add also a variant with small letter starting preposition => "van Eyck"
					if (not subname[0].islower()):
						names.add(subname[0].lower() + subname[1:])

		for role in roles_lower:
			names.add(role)
			names.add(role.capitalize())
			names.add(role.title())
			if self.get_ROLE_PREFIX():
				role = self.get_ROLE_PREFIX().lower() + role
				names.add(role)
				names.add(role.capitalize())
				names.add(role.title()) # For english - every first letter is upper

		return names

	@classmethod
	def add_to_dictionary_by_config(self, subname, dictionary, config = AutomataVariants.DEFAULT):
		dictionary.add(subname.lower() if AutomataVariants.isLowercase(config) else subname)
