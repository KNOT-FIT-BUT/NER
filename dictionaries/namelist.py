 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import regex
import sys

from abc import ABC, abstractmethod

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
	
	re_flag_names = r"(?:#[A-Z0-9]E?)"
	re_flag_only1st_firstname = r"(?:#[GI]E?)"
	re_flag_firstname = r"(?:#[G]E?)"
	re_flag_sure_surname = r"(?:#[^GI]E?)"

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
		unwanted_match = set([',', '[0-9]']) | self.reEscapeSet(self.getSaintVariants()) | self.reEscapeSet(self.getLangUnwantedMatch())
		return regex.compile(r'({})'.format('|'.join(unwanted_match)))


	def entry2dict(self, _key, _value):
		if _key not in self.dictionary:
			self.dictionary[_key] = set()
		self.dictionary[_key].add(_value)


	def getNonAccentKey(self, _key, nonacc_type):
		return nonacc_type + ":\t" + _key

	def add(self, _key, _value, _type):
		"""
		Adds the name into the dictionary. For each name it adds also an alternative without accent.

		_key : the name
		_value : the line number (from the KB) corresponding to a given entity
		_type : the type prefix for a given entity
		"""


		_key = regex.sub(r"#[A-Za-z0-9]E?(?= |,|\.|-|–|$)", "", _key)
		if '\u200b' in _key:
			self.add(regex.sub(r"\u200b *", ' ', _key), _value, _type) # Add new key with space instead of zero width space (including insurance against presence of multiple space due to added new one)
			_key = regex.sub(r"#[A-Za-z0-9]+\u200b", '', _key) # Remove word mark including zero width space

		_key = regex.sub(r"#L(?=[0-9])", "", _key) # temporary fix for mountains like K#L12, K#L2, ... (will be solved by extra separator by M. Dočekal)
		_key = regex.sub(r"(?<=\.)#4", "", _key) # temporary fix for ordinals like <something> 1.#4díl, ... (will be solved by extra separator by M. Dočekal)

		_key = _key.strip()

		if AutomataVariants.NONACCENT & self.automata_variants:
			_key = remove_accent(_key.lower())

		if AutomataVariants.LOWERCASE & self.automata_variants:
			_key = _key.lower()

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
				

	def addVariants(self, _key, _nametype, _value, _type_set, _fields):
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
		if _key not in self.lst_allowed:

			# we don't want names with any of these characters
			unsuitable = ";?!()[]{}<>/~@#$%^&*_=+|\"\\"
			_key = _key.strip()
			for x in unsuitable:
				if x in _key:
					return

			# inspecting names with numbers
			if len(regex.findall(r"[0-9]+", _key)) != 0:
				# we don't want entities containing only numbers
				if len(regex.findall(r"^[0-9 ]+$", _key)) != 0:
					return
				# exception for people or artist name (e.g. John Spencer, 1st Earl Spencer)
				if 'person' in _type_set:
					if len(regex.findall(r"[0-9]+(st|nd|rd|th)", _key)) == 0:
						return
				# we don't want locations with numbers at all
				elif 'geographical' in _type_set:
					return

			# special filtering for people and artists
			if 'person' in _type_set:
				# we don't want names starting with "List of"
				if _key.startswith("Seznam "):
					return

			# generally, we don't want names starting with low characters (event is needed with low character, ie. "bitva u Waterloo")
			if not 'event' in _type_set:
				if len(regex.findall(r"^\p{Ll}+", _key)) != 0:
					return

			# filtering out all names with length smaller than 2 and greater than 80 characters
			if len(_key) < 2 or len(_key) > 80:
				return

			# filtering out names ending by ., characters
			if 'person' in _type_set:
				if len(regex.findall(r"[.,]$", _key)) != 0:
					print('Skipped part "filtering out names ending by .,  characters" for name: {}'.format(_key),  file = sys.stderr) # Karel IV. was filtered out => monitoring for which names this is useful (was intended)
					#return

		# Get all inflection variants of key
		key_inflections = None
		if _key in self.alternatives:
			key_inflections = self.alternatives[_key]
		if not key_inflections:
			key_inflections = set([_key]) # TODO alternative names are not in subnames
			if 'person' in _type_set and _nametype != "nick":
				self.subnames |= self.persons.get_normalized_subnames(set([_key]), separate_to_names = True)
		for tmp in key_inflections.copy():
			if regex.search(r"(?:-|–)\p{Lu}", tmp):
				key_inflections.add(regex.sub(r"(?:-|–)(\p{Lu})", " \g<1>", tmp)) # Payne-John Christo -> Payne John Christo

		# All following transformatios will be performed for each of inflection variant of key_inflection
		for key_inflection in key_inflections:
			# adding name into the dictionary
			self.add(key_inflection, _value, _type_set)

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
				if _nametype != "nick":
					if regex.search(r"#", key_inflection):
						# TODO: what about abbreviation of Mao ce-Tung?
						#                             ( <firstname>             ) ( <other firstnames>                                 )( <unknowns>               )( <surnames>                   )
						name_parts = regex.search(r"^((?:\p{Lu}')?\p{Lu}\p{L}+%s) ((?:(?:(?:\p{Lu}')?\p{L}+#I )*(?:\p{Lu}')?\p{L}+%s )*)((?:(?:\p{Lu}')?\p{L}+#I )*)((?:\p{Lu}')?\p{Lu}\p{L}+(%s).*)$" % (self.re_flag_only1st_firstname, self.re_flag_firstname, self.re_flag_sure_surname), key_inflection)
						if name_parts:
							fn_1st = name_parts.group(1)
							tmp_fn_others = name_parts.group(2).strip().split()
							n_unknowns = name_parts.group(3).strip().split()
							tmp_sn_all = name_parts.group(4)
							if name_parts.group(5) in ['#S', '#SE']:
								for i in range(len(n_unknowns) + 1):
									sep_special = ""
									fn_others_full = ""
									fn_others_abbr = ""

									fn_others = tmp_fn_others + n_unknowns[:i]
									if len(fn_others):
										sep_special = " "
										fn_others_full += " ".join(fn_others)
										for fn_other in fn_others:
											fn_others_abbr += fn_other[:1] + ". "
										fn_others_abbr = fn_others_abbr.strip()

									sn_all = ' '.join(n_unknowns[i:])
									if sn_all:
										sn_all += ' ' + tmp_sn_all
									else:
										sn_all = tmp_sn_all

									# For all of following format exaplaining comments of additions let us assume, that Johann Gottfried Bernhard is firstnames and a surname is Bach only.
									self.add("{} {}{}{}".format(fn_1st, fn_others_abbr, sep_special, sn_all), _value, _type_set)       # Johann G. B. Bach
									self.add("{}. {}{}{}".format(fn_1st[:1], fn_others_abbr, sep_special, sn_all), _value, _type_set)  # J. G. B. Bach
									self.add("{} {}".format(fn_1st, sn_all), _value, _type_set)                                        # Johann Bach
									self.add("{}. {}".format(fn_1st[:1], sn_all), _value, _type_set)                                   # J. Bach
									self.add("{}, {}{}{}".format(sn_all, fn_1st, sep_special, fn_others_full), _value, _type_set)      # Bach, Johann Gottfried Bernhard
									self.add("{}, {}{}{}".format(sn_all, fn_1st, sep_special, fn_others_abbr), _value, _type_set) # Bach, Johann G. B.
									self.add("{}, {}.{}{}".format(sn_all, fn_1st[:1], sep_special, fn_others_abbr), _value, _type_set) # Bach, J. G. B.
									self.add("{}, {}".format(sn_all, fn_1st), _value, _type_set)                                       # Bach, Johann
									self.add("{}, {}.".format(sn_all, fn_1st[:1]), _value, _type_set)                                  # Bach, J.

					else:
						self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>", key_inflection), _value, _type_set) # Adolf Born -> A. Born
						self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>", key_inflection), _value, _type_set) # Peter Paul Rubens -> P. P. Rubens
						self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>", key_inflection), _value, _type_set) # Peter Paul Rubens -> Peter P. Rubens
						self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>. \g<4>", key_inflection), _value, _type_set) # Johann Gottfried Bernhard Bach -> J. G. B. Bach
						self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3> \g<4>", key_inflection), _value, _type_set) # Johann Gottfried Bernhard Bach -> J. G. Bernhard Bach
						self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>. \g<4>", key_inflection), _value, _type_set) # Johann Gottfried Bernhard Bach -> Johann G. B. Bach
						self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3> \g<4>", key_inflection), _value, _type_set) # Johann Gottfried Bernhard Bach -> Johann G. Bernhard Bach
						self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2> \g<3>. \g<4>", key_inflection), _value, _type_set) # Johann Gottfried Bernhard Bach -> Johann Gottfried B. Bach
						if not regex.search("[IVX]\.", key_inflection): # do not consider "Karel IV." or "Albert II. Monacký", ...
							self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2>, \g<1>", key_inflection), _value, _type_set) # Adolf Born -> Born, Adolf
							self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<2>, \g<1>.", key_inflection), _value, _type_set) # Adolf Born -> Born, A.
							self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<3>, \g<1> \g<2>", key_inflection), _value, _type_set) # Johann Joachim Quantz -> Quantz, Johann Joachim
							self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<3>, \g<1>. \g<2>.", key_inflection), _value, _type_set) # Johann Joachim Quantz -> Quantz, J. J.
							self.add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>", key_inflection), _value, _type_set) # Tomáš Garrigue Masaryk -> Garrigue Masaryk, Tomáš
							self.add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>.", key_inflection), _value, _type_set) # Tomáš Garrigue Masaryk -> Garrigue Masaryk, T.
				if "Mc" in key_inflection:
					self.add(regex.sub(r"Mc(\p{Lu})", "Mc \g<1>", key_inflection), _value, _type_set) # McCollum -> Mc Collum
					self.add(regex.sub(r"Mc (\p{Lu})", "Mc\g<1>", key_inflection), _value, _type_set) # Mc Collum -> McCollum
				if "." in key_inflection:
					new_key_inflection = regex.sub(r"(\p{Lu}\.)%s? (?=\p{Lu})" % self.re_flag_names, "\g<1>", key_inflection) # J. M. W. Turner -> J.M.W.Turner
					self.add(new_key_inflection, _value, _type_set)
					new_key_inflection = regex.sub(r"(\p{Lu}\.)%s?(?=\p{Lu}\p{L}+)" % self.re_flag_names, "\g<1> ", new_key_inflection) # J.M.W.Turner -> J.M.W. Turner
					self.add(new_key_inflection, _value, _type_set)
					self.add(regex.sub(r"\.%s" % self.re_flag_names, "", new_key_inflection), _value, _type_set) # J.M.W. Turner -> JMW Turner
				if "-" in key_inflection: # 0x45
					self.add('-'.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in key_inflection.split("-")), _value, _type_set) # Mao Ce-tung -> Mao Ce-Tung
				if "–" in key_inflection: # 0x96
					self.add('–'.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in key_inflection.split("–")), _value, _type_set) # Mao Ce-tung -> Mao Ce–Tung
				if "ì" in key_inflection:
					self.add(regex.sub("ì", "í", key_inflection), _value, _type_set) # Melozzo da Forlì -> Melozzo da Forlí

				parts = key_inflection.split(" ")
				# if a name contains any of these words, we will not create permutations
				if not (set(parts) & set(["von", "van"])):
					for x in self.lst_freqterms:
						if x in key_inflection:
							new_key_inflection = regex.sub(' ?,? ' + x + '$', '', key_inflection) # John Brown, Jr. -> John Brown
							new_key_inflection = regex.sub('^' + x + ' ', '', new_key_inflection) # Sir Patrick Stewart -> Patrick Stewart
							if new_key_inflection.count(' ') >= 1:
								self.add(new_key_inflection, _value, _type_set)

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


	def generateDict(self, include_extra = False):
		if include_extra:
			# Subnames in all inflections with 'N'
			for subname in self.subnames:
				self.entry2dict(subname, 'N')

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


	def getTsv(self, include_extra = False, outfile = sys.stdout):
		for item in self.generateDict(include_extra).items():
			print(item[0] + "\t" + ";".join(item[1]), file = outfile)
