 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import regex
import sys

from abc import ABC, abstractmethod
from typing import Dict, List, Set, TextIO

import metrics_knowledge_base

from libs.automata_variants import AutomataVariants
from libs.utils import remove_accent
from libs.entities.entity_loader import EntityLoader
from libs.lib_loader import LibLoader
from libs.nationalities.nat_loader import NatLoader

class Namelist(ABC):
	NONACCENT_TYPES = set(['person', 'geographical'])

	dictionary = {}
	subnames = set()
	automata_variants = AutomataVariants.DEFAULT
	kb_struct = None

	freqterms = []
	lst_allowed = []
	alternatives = {}

	re_flag_names = r"(?:#[A-Z0-9]+E?)"
	re_flag_only1st_firstname = r"(?:#j?[GI]E?)"
	re_flag_firstname = r"(?:#j?[G]E?)"
	re_flag_sure_surname = r"(?:#j?[^GI]E?)"

	def __init__(self, lang):
		self.lang = lang
		self.ntokb = NatLoader.load(lang)

		self.re_saint = r'({})\s'.format('|'.join(self.reEscapeSet(self.getSaintVariants())))    # Regex for all inflections of "Svatý" (or particular language variant)
		self.saint_abb = self.getSaintAbb().strip().rstrip('.')
		escaped_saint_abb = regex.escape(self.saint_abb)
		self.re_saint_abb_only = r'{}\s'.format(escaped_saint_abb)    # Regex for "Sv " for example in "Sv Jan"
		self.re_saint_abb_dot = r'{}\.\s?'.format(escaped_saint_abb)  # Regex for "Sv. " for example in "Sv. Jan" or "Sv." in "Sv.Jan"
		self.re_saint_abbs = r'({}|{})'.format(self.re_saint_abb_dot, self.re_saint_abb_only) # common regex for both of previous 2
		self.persons = EntityLoader.load(module = 'persons', lang = lang, initiate = 'Persons')


	@abstractmethod
	def getSaintVariants(self):
		raise NotImplementedError('Missing implementation of getSaintVariants()');


	@abstractmethod
	def getSaintAbb(self):
		raise NotImplementedError('Missing implementation of getSaintAbb()');


	@abstractmethod
	def getLangUnwantedMatch(self):
		return set()


	def setAllowed(self, lst_allowed):
		self.lst_allowed = lst_allowed


	def setAlternatives(self, alternatives):
		self.alternatives = alternatives


	def setAutomataVariants(self, automata_variants):
		self.automata_variants = automata_variants


	def setFreqTerms(self, lst_freqterms):
		self.lst_freqterms = lst_freqterms


	def setKBStruct(self, kb_struct):
		self.kb_struct = kb_struct


	def addSubnames(self, subnames):
		self.subnames = self.subnames | subnames


	def reEscapeSet(self, set2escape):
		return set([regex.escape(x) for x in set2escape])


	def reUnwantedMatch(self):
		unwanted_match = self.reEscapeSet(self.getSaintVariants()) | self.reEscapeSet(self.getLangUnwantedMatch())
		return regex.compile(r'(,|[0-9]|(^|\s)({})(\s|$))'.format('|'.join(unwanted_match)))


	def entry2dict(self, key: str, link: str) -> None:
		if key not in self.dictionary:
			self.dictionary[key] = set()
		self.dictionary[key].add(link)


	def getNonAccentKey(self, key: str, nonacc_type: str) -> str:
		return nonacc_type + ":\t" + key

	def add(self, _key, _value, _type):
		"""
		Adds the name into the dictionary. For each name it adds also an alternative without accent.

		_key : the name
		_value : the line number (from the KB) corresponding to a given entity
		_type : the type prefix for a given entity
		"""


		_key = regex.sub(r"#[A-Za-z0-9]+E?(?= |,|\.|-|–|$)", "", _key)
		if '\u200b' in _key:
			self.add(regex.sub(r"\u200b *", ' ', _key), _value, _type) # Add new key with space instead of zero width space (including insurance against presence of multiple space due to added new one)
			_key = regex.sub(r"#[A-Za-z0-9]+\u200b", '', _key) # Remove word mark including zero width space

		_key = regex.sub(r"#L(?=[0-9])", "", _key) # temporary fix for mountains like K#L12, K#L2, ... (will be solved by extra separator by M. Dočekal)
		_key = regex.sub(r"(?<=\.)#4", "", _key) # temporary fix for ordinals like <something> 1.#4díl, ... (will be solved by extra separator by M. Dočekal)

		_key = _key.strip()

		_key = self._get_key_by_atm_variant(key=_key)

		# removing entities that begin with '-. or space
		if len(regex.findall(r"^[ '-\.]", _key)) != 0:
			return

		# adding the type-specific prefix to begining of the name
		if AutomataVariants.NONACCENT & self.automata_variants:
			valid_type = False
			for nonacc_type in self.NONACCENT_TYPES:
				if nonacc_type in _type:
					valid_type = True
					# adding the name into the dictionary
					self.entry2dict(self.getNonAccentKey(_key, nonacc_type), _value)

			if not valid_type:
				self.entry2dict(self.getNonAccentKey(_key, 'other'), _value)
		else:
			self.entry2dict(_key, _value)


	def add_variants(self, _key: str, _nametype: str, _value: str, _type_set: Set[str], _fields: List[str]) -> None:
		"""
		Adds the name into the dictionary. For each name it adds also an alternative without accent.

		_key : the name of a given entity
		_value : the line number (from the KB) corresponding to a given entity
		_type_set : the type of a given entity
		"""

		if self.kb_struct is None:
			raise Exception('ERROR: KB Struct was probably not set by setKBStruct() method.')

		# removing white spaces
		_key = regex.sub('\s+', ' ', _key).strip()

		# there are no changes for the name from the allow list
		if _key not in self.lst_allowed and self._is_unsuitable_key(key=_key, type_set=_type_set):
			return

		# All following transformatios will be performed for each of inflection variant of key_inflection
		for key_inflection in self._get_key_inflections(key=_key, nametype=_nametype, type_set=_type_set):
			# adding name into the dictionary
			self.add(key_inflection, _value, _type_set)

			# TODO: maybe for not-#-flagged only?
			# generating permutations for person and artist names
			if 'person' in _type_set:
				length = key_inflection.count(" ") + 1
				if length <= 4 and length > 1:
					parts = key_inflection.split(" ")
					# if a name contains any of these words, we will not create permutations
					if not (set(parts) & set(["van", "von"])):
						names = list(itertools.permutations(parts))
						for x in names:
							r = " ".join(x)
							self.add(key_inflection, _value, _type_set)

			# adding various alternatives for given types
			if not 'event' in _type_set:
				if regex.search(self.re_saint, key_inflection) is not None or regex.search(self.re_saint_abbs, key_inflection) is not None:
					saint_abb_name = regex.sub(r'({}|{})'.format(self.re_saint, self.re_saint_abbs), '{}. '.format(self.saint_abb), key_inflection) # Svatý Jan / Sv.Jan / Sv Jan -> Sv. Jan
					self.add(saint_abb_name, _value, _type_set)
					self.add(regex.sub(r'(?<=(^|\s)){}(?=\p{{Lu}})'.format(self.re_saint_abb_dot), '{}.'.format(self.saint_abb), saint_abb_name), _value, _type_set) # Sv. Jan -> Sv.Jan (Svatý Jan / Sv. Jan / Sv Jan -> Sv.Jan)
					self.add(regex.sub(r'(?<=(^|\s)){}(?=\p{{Lu}})'.format(self.re_saint_abb_dot), '{} '.format(self.saint_abb), saint_abb_name), _value, _type_set) # Sv. Jan -> Sv Jan (Svatý Jan / Sv. Jan / Sv.Jan -> Sv Jan)
					# TODO: base form for female and middle-class
					for saint_variant in self.getSaintVariants():
						self.add(regex.sub(r'(?<=(^|\s)){}(?=\p{{Lu}})'.format(self.re_saint_abbs), '{} '.format(saint_variant), key_inflection), _value, _type_set) # Sv. Jan / Sv.Jan / Sv Jan -> Svatý Jan / Svatá Jan / Svaté Jan / ...

			if 'person' in _type_set:
				self._add_person_variants(
					key_inflection=key_inflection,
					nametype=_nametype,
					link=_value,
					type_set=_type_set,
				)

			if 'geographical' in _type_set:
				description = self.kb_struct.get_data_for(_fields, 'DESCRIPTION')
				if key_inflection in description:
					country = self.kb_struct.get_data_for(_fields, 'COUNTRY')
					if country and country not in key_inflection:
						self.add(key_inflection + ", " + country, _value, _type_set) # Peking -> Peking, China
						self.add(regex.sub("United States", "US", key_inflection + ", " + country), _value, _type_set)

			#if 'event' in _type_set:
			#	if len(regex.findall(r"^[0-9]{4} (Summer|Winter) Olympics$", key_inflection)) != 0:
			#		location = self.kb_struct.get_data_for(_fields, 'LOCATIONS')
			#		year = self.kb_struct.get_data_for(_fields, 'START DATE')[:4]
			#		if year and location and "|" not in location:
			#			self.add("Olympics in " + location + " in " + year, _value, _type_set) # 1928 Summer Olympics -> Olympics in Amsterdam in 1928
			#			self.add("Olympics in " + year + " in " + location, _value, _type_set) # 1928 Summer Olympics -> Olympics in 1928 in Amsterdam
			#			self.add("Olympic Games in " + location + " in " + year, _value, _type_set) # 1928 Summer Olympics -> Olympic Games in Amsterdam in 1928
			#			self.add("Olympic Games in " + year + " in " + location, _value, _type_set) # 1928 Summer Olympics -> Olympic Games in 1928 in Amsterdam


	def get_tsv(self, include_extra: bool = False, outfile: TextIO = sys.stdout) -> None:
		for item in self._generate_dict(include_extra).items():
			print(item[0] + "\t" + ";".join(item[1]), file = outfile)

	def _add_person_variants(self, key_inflection: str, nametype: str, link: str, type_set: Set[str]) -> None:
		if nametype != "nick":
			if regex.search(r"#", key_inflection):
				self._add_tagged_person_alternatives_variants(key_inflection=key_inflection, link=link, type_set=type_set)
			else:
				self._add_untagged_person_variants(key_inflection=key_inflection, link=link, type_set=type_set)
		if "Mc" in key_inflection:
			self.add(regex.sub(r"Mc(\p{Lu})", "Mc \g<1>", key_inflection), link, type_set) # McCollum -> Mc Collum
			self.add(regex.sub(r"Mc (\p{Lu})", "Mc\g<1>", key_inflection), link, type_set) # Mc Collum -> McCollum
		if "." in key_inflection:
			new_key_inflection = regex.sub(r"(\p{Lu}\.)%s? (?=\p{Lu})" % self.re_flag_names, "\g<1>", key_inflection) # J. M. W. Turner -> J.M.W.Turner
			self.add(new_key_inflection, link, type_set)
			new_key_inflection = regex.sub(r"(\p{Lu}\.)%s?(?=\p{Lu}\p{L}+)" % self.re_flag_names, "\g<1> ", new_key_inflection) # J.M.W.Turner -> J.M.W. Turner
			self.add(new_key_inflection, link, type_set)
			self.add(regex.sub(r"\.%s" % self.re_flag_names, "", new_key_inflection), link, type_set) # J.M.W. Turner -> JMW Turner
		if "-" in key_inflection: # 0x45
			self.add('-'.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in key_inflection.split("-")), link, type_set) # Mao Ce-tung -> Mao Ce-Tung
		if "–" in key_inflection: # 0x96
			self.add('–'.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in key_inflection.split("–")), link, type_set) # Mao Ce-tung -> Mao Ce–Tung
		if "ì" in key_inflection:
			self.add(regex.sub("ì", "í", key_inflection), link, type_set) # Melozzo da Forlì -> Melozzo da Forlí

		parts = key_inflection.split(" ")
		# if a name contains any of these words, we will not create permutations
		if not (set(parts) & set(["von", "van"])):
			for x in self.lst_freqterms:
				if x in key_inflection:
					new_key_inflection = regex.sub(' ?,? ' + x + '$', '', key_inflection) # John Brown, Jr. -> John Brown
					new_key_inflection = regex.sub('^' + x + ' ', '', new_key_inflection) # Sir Patrick Stewart -> Patrick Stewart
					if new_key_inflection.count(' ') >= 1:
						self.add(new_key_inflection, link, type_set)

	def _add_tagged_person_alternatives_variants(self, key_inflection: str, link: str, type_set: Set[str]) -> None:
		nameparts = self._get_tagged_person_nameparts(key_inflection=key_inflection)

		if nameparts == {} or nameparts['sn_last_flags'] not in ['#S', '#SE', '#jS', '#jSE']:
			return

		for i in range(len(nameparts['n_unknowns']) + 1):
			sep_special = ""
			fn_possible_others_full = ""
			fn_possible_others_abbr = ""

			fn_possible_others = nameparts['fn_others'] + nameparts['n_unknowns'][:i]
			if len(fn_possible_others):
				sep_special = " "
				fn_possible_others_full += " ".join(fn_possible_others)
				for fn_possible_other in fn_possible_others:
					fn_possible_others_abbr += fn_possible_other[:1] + ". "
				fn_possible_others_abbr = fn_possible_others_abbr.strip()

			sn_full_variants = {}
			sn_unknowns = ' '.join(nameparts['n_unknowns'][i:])
			if sn_unknowns:
				sn_unknowns += ' '

			sn_full_alternatives = {sn_unknowns + nameparts['sn_full'], sn_unknowns + nameparts['n_partonyms'] + nameparts['sn_full']}

			for sn_full in sn_full_alternatives:
				self._add_tagged_person_variants(
					fn_1st=nameparts['fn_1st'],
					fn_others_full=fn_possible_others_full,
					fn_others_abbr=fn_possible_others_abbr,
					sep_special=sep_special,
					sn_full=sn_full,
					link=link,
					type_set=type_set,
				)

	def _add_tagged_person_variants(self, fn_1st: str, fn_others_full: str, fn_others_abbr: str, sep_special: str, sn_full: str, link: str, type_set: Set[str]) -> None:
		# For all of following format exaplaining comments of additions let us assume, that Johann Gottfried Bernhard is firstnames and a surname is Bach only.
		self.add("{} {}{}{}".format(fn_1st, fn_others_abbr, sep_special, sn_full), link, type_set)       # Johann G. B. Bach
		self.add("{}. {}{}{}".format(fn_1st[:1], fn_others_abbr, sep_special, sn_full), link, type_set)  # J. G. B. Bach
		self.add("{} {}".format(fn_1st, sn_full), link, type_set)                                        # Johann Bach
		self.add("{}. {}".format(fn_1st[:1], sn_full), link, type_set)                                   # J. Bach
		self.add("{}, {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_full), link, type_set)      # Bach, Johann Gottfried Bernhard
		self.add("{}, {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_abbr), link, type_set)      # Bach, Johann G. B.
		self.add("{}, {}.{}{}".format(sn_full, fn_1st[:1], sep_special, fn_others_abbr), link, type_set) # Bach, J. G. B.
		self.add("{}, {}".format(sn_full, fn_1st), link, type_set)                                       # Bach, Johann
		self.add("{}, {}.".format(sn_full, fn_1st[:1]), link, type_set)                                  # Bach, J.

	def _add_untagged_person_variants(self, key_inflection: str, link: str, type_set: Set[str]) -> None:
		self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>", key_inflection), link, type_set)   # Adolf Born -> A. Born
		self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>", key_inflection), link, type_set)   # Peter Paul Rubens -> P. P. Rubens
		self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>", key_inflection), link, type_set)    # Peter Paul Rubens -> Peter P. Rubens
		self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<3>", key_inflection), link, type_set)           # Peter Paul Rubens -> Peter Rubens
		self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>. \g<4>", key_inflection), link, type_set)   # Johann Gottfried Bernhard Bach -> J. G. B. Bach
		self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3> \g<4>", key_inflection), link, type_set)    # Johann Gottfried Bernhard Bach -> J. G. Bernhard Bach
		self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>. \g<4>", key_inflection), link, type_set)    # Johann Gottfried Bernhard Bach -> Johann G. B. Bach
		self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3> \g<4>", key_inflection), link, type_set)     # Johann Gottfried Bernhard Bach -> Johann G. Bernhard Bach
		self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2> \g<3>. \g<4>", key_inflection), link, type_set)     # Johann Gottfried Bernhard Bach -> Johann Gottfried B. Bach
		if not regex.search("[IVX]\.", key_inflection): # do not consider "Karel IV." or "Albert II. Monacký", ...
			self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2>, \g<1>", key_inflection), link, type_set)    # Adolf Born -> Born, Adolf
			self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<2>, \g<1>.", key_inflection), link, type_set)   # Adolf Born -> Born, A.
			self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<3>, \g<1> \g<2>", key_inflection), link, type_set)     # Johann Joachim Quantz -> Quantz, Johann Joachim
			self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<3>, \g<1>. \g<2>.", key_inflection), link, type_set)   # Johann Joachim Quantz -> Quantz, J. J.
			self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>", key_inflection), link, type_set)     # Tomáš Garrigue Masaryk -> Garrigue Masaryk, Tomáš
			self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>.", key_inflection), link, type_set)    # Tomáš Garrigue Masaryk -> Garrigue Masaryk, T.


	def _generate_dict(self, include_extra: bool = False) -> Dict:
		if include_extra:
			# Subnames in all inflections with 'N'
			for subname in self.subnames:
				self.entry2dict(self._get_key_by_atm_variant(key=subname), 'N')

			"""
			# Pronouns with first lower and first upper with 'N'
			word_types = LibLoader.load('word_types', self.lang, 'WordTypes')
			pronouns = list(word_types.PRONOUNS.keys())
			if not (AutomataVariants.LOWERCASE & self.automata_variants):
				pronouns += [pronoun.capitalize() for pronoun in pronouns]
			if AutomataVariants.NONACCENT & self.automata_variants:
				pronouns += [remove_accent(pronoun) for pronoun in pronouns]
			self.dictionary.update(dict.fromkeys(pronouns, 'N'))

			# geting jurisdictions
			jurisdictions = self.ntokb.get_jurisdictions()
			for jur in jurisdictions:
				self.entry2dict(jur, 'N')
			"""

		return self.dictionary

	def _get_key_by_atm_variant(self, key: str) -> str:
		if AutomataVariants.NONACCENT & self.automata_variants:
			return remove_accent(key.lower())

		if AutomataVariants.LOWERCASE & self.automata_variants:
			return key.lower()

		return key

	def _get_key_inflections(self, key: str, nametype: str, type_set: Set[str]) -> Dict:
		key_inflections = None

		if key in self.alternatives:
			key_inflections = self.alternatives[key]
		if not key_inflections:
			key_inflections = set([key]) # TODO alternative names are not in subnames
			if 'person' in type_set and nametype != 'nick':
				self.subnames |= self.persons.get_normalized_subnames(set([key]), separate_to_names = True)
		for tmp in key_inflections.copy():
			if regex.search(r"(?:-|–)\p{Lu}", tmp):
				key_inflections.add(regex.sub(r"(?:-|–)(\p{Lu})", " \g<1>", tmp)) # Payne-John Christo -> Payne John Christo

		return key_inflections

	def _get_tagged_person_nameparts(self, key_inflection: str) -> Dict:
		nameparts = {}
		#                       ( <firstname>                           ) ( <other firstnames>                                           )( <partonyms>                         )( <unknowns>                           )( <surnames>                   )
		parts = regex.search(r"^(?P<firstname>(?:\p{Lu}')?\p{Lu}\p{L}+%s) (?P<others>(?:(?:(?:\p{Lu}')?\p{L}+#I )*(?:\p{Lu}')?\p{L}+%s )*)(?P<partonyms>(?:\p{Lu}\p{L}+#j[PQ] )*)(?P<unknowns>(?:(?:\p{Lu}')?\p{L}+#I )*)(?P<surnames>(?:\p{Lu}')?\p{Lu}\p{L}+(?<surname_flags>%s).*)$" % (self.re_flag_only1st_firstname, self.re_flag_firstname, self.re_flag_sure_surname), key_inflection)
		if parts:
			nameparts = {
				'fn_1st': parts.group('firstname'),
				'fn_others': parts.group('others').strip().split(),
				'n_unknowns': parts.group('unknowns').strip().split(),
				'n_partonyms': parts.group('partonyms'),
				'sn_full': parts.group('surnames'),
				'sn_last_flags': parts.group('surname_flags')
			}
		return nameparts


	def _is_unsuitable_key(self, key: str, type_set: Set) -> bool:
		# we don't want names with any of these characters
		unsuitable = ";?!()[]{}<>/~@#$%^&*_=+|\"\\"
		for x in unsuitable:
			if x in key:
				return True

		# inspecting names with numbers
		if len(regex.findall(r"[0-9]+", key)) != 0:
			# we don't want entities containing only numbers
			if len(regex.findall(r"^[0-9 ]+$", key)) != 0:
				return True
			# exception for people or artist name (e.g. John Spencer, 1st Earl Spencer)
			if 'person' in type_set:
				if len(regex.findall(r"[0-9]+(st|nd|rd|th)", key)) == 0:
					return True
			# we don't want locations with numbers at all
			elif 'geographical' in type_set:
				return True

		# special filtering for people and artists
		if 'person' in type_set:
			# we don't want names starting with "List of"
			if key.startswith("Seznam "):
				return True

		# generally, we don't want names starting with low characters (event is needed with low character, ie. "bitva u Waterloo")
		if not 'event' in type_set:
			if len(regex.findall(r"^\p{Ll}+", key)) != 0:
				return True

		# filtering out all names with length smaller than 2 and greater than 80 characters
		if len(key) < 2 or len(key) > 80:
			return True

		return False
