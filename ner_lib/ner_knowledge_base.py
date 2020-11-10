#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=4 softtabstop=4 noexpandtab shiftwidth=4

"""
Copyright 2015 Brno University of Technology

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Author: Matej Magdolen, xmagdo00@stud.fit.vutbr.cz
# Author: Jan Doležal, xdolez52@stud.fit.vutbr.cz
# Author: Lubomír Otrusina, iotrusina@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vutbr.cz
#
# Description: Loads a shared knowledge base.

import itertools
import os
import pickle
from importlib.machinery import SourceFileLoader

# <LOKÁLNÍ IMPORTY>
from .kb_daemon import KbDaemon
from .configs import DIRPATH_KB_DAEMON, INPUTS_DIR, KB_MULTIVALUE_DELIM
from ..libs.utils import remove_accent
from ..libs.entities.entity_loader import EntityLoader

# Pro debugování:
from .debug import print_dbg_en
# </LOKÁLNÍ IMPORTY>


class KnowledgeBase():
	def __init__(self, lang):
		self.lang = lang
		self.personUtils = EntityLoader.load(module = 'persons', lang = self.lang, initiate = 'Persons')
		self.path_kb = os.path.abspath(os.path.join(INPUTS_DIR, self.lang, "KB_all.tsv"))
	
	'''
	Třída zapouzdřující KB.
	'''

	def init(self, kb_shm_name=None):
		'''
		Inicializace.
		'''

		KB_shm = SourceFileLoader('KB_shm', os.path.join(DIRPATH_KB_DAEMON, "KB_shm.py")).load_module()
		self.kb_shm_name = kb_shm_name
		self.kb_shm = KB_shm.KB_shm(self.kb_shm_name)
		self.kb_daemon = None


	def start(self):
		'''
		Připojí sdílenou paměť.
		'''

		kb_daemon_run = self.check()

		try:
			if self.kb_shm_name == None:
				self.init("/decipherKB-daemon_shm-%s" % (self.kb_shm.getVersionFromSrc(self.path_kb)))
				return self.start()
			else:
				if kb_daemon_run:
					self.kb_shm.start()
					if not self.checkVersion():
						raise RuntimeError("\"%s\" has different version compared to \"%s\"." % (self.kb_shm_name, self.path_kb))
				else:
					self.kb_daemon = KbDaemon(self.path_kb, kb_shm_name=self.kb_shm_name)
					self.kb_daemon.start()
					self.kb_shm.start()

		except:
			self.end()
			raise


	def end(self):
		'''
		Odpojí sdílenou paměť.
		'''

		if self.kb_daemon:
			self.kb_daemon.stop()
		self.kb_shm.end()
		self.kb_daemon = None


	def check(self):
		'''
		Zkontroluje, zda je sdílená paměť k dispozici.
		'''
		return self.kb_shm.check()


	def checkVersion(self):
		'''
		Zkontroluje, zda je ve sdílené paměti stejná verze KB jako v PATH_KB.
		'''
		return self.version() == self.kb_shm.getVersionFromSrc(self.path_kb)


	def version(self):
		'''
		Vrátí číslo verze KB ve sdílené paměti.
		'''
		return self.kb_shm.version()


	def initName_dict(self):
		'''
		Dictionary asociates parts of person names with corresponding items of knowledge base.
		'''

		PATH_NAMEDICT = os.path.join(INPUTS_DIR, self.lang, "ner_namedict.pkl")
		#PATH_FRAGMENTS = os.path.join(INPUTS_DIR, self.lang, "ner_fragments.pkl")

		self.name_dict = {}
		self.fragments = set()

		# Proto aby se nemusela znova procházet KB, vytvoří se soubor PATH_NAMEDICT.
		# Namedict se bude načítat z něj pokud PATH_KB bude starší než PATH_NAMEDICT - tím dojde k urychlení.
		if (os.access(PATH_NAMEDICT, os.F_OK)) and (os.stat(self.path_kb).st_mtime < os.stat(PATH_NAMEDICT).st_mtime and os.path.getsize(PATH_NAMEDICT)):
			with open(PATH_NAMEDICT, 'rb') as namedict_file:
				version, self.name_dict, self.fragments = pickle.load(namedict_file)
		else:
			version = -1

		if version != self.version():
			self.fragments = set()
			namedict_file = open(PATH_NAMEDICT, 'wb')
			line = 1
			text = self.get_data_at(line, 1)

			while text != None:
				ent_type_set = self.get_ent_type(line)

				if "person" in ent_type_set:
					whole_names = self.get_data_for(line, "ALIASES", separator = KB_MULTIVALUE_DELIM)
					whole_names.append(self.get_data_for(line, "NAME"))

					# creates subnames
					names = self.personUtils.get_normalized_subnames(whole_names, roles = self.get_data_for(line, "ROLES", separator = KB_MULTIVALUE_DELIM), separate_to_names = True)

					for name in names:
						name = remove_accent(name).lower()
						if name not in self.name_dict:
							self.name_dict[name] = set([line])
						else:
							self.name_dict[name].add(line)
				line += 1
				text = self.get_data_at(line, 1)
			pickle.dump((self.version(), self.name_dict, self.fragments), namedict_file, pickle.HIGHEST_PROTOCOL)

			namedict_file.close()


	def print_subnames(self):
		'''
		Print all partial name variants from self.name_dict.
		'''
		for fragment in self.fragments:
			print(fragment)


	def get_field(self, line, column):
		'''
		Zavrhovaná metoda!
		Číslování řádků od 1 a sloupců od 0, podle "ner.py".
		Ovšem SharedKB čísluje řádky i sloupce od 1.
		'''

		return self.kb_shm.dataAt(line, column + 1)


	def get_data_at(self, line, col):
		'''
		Číslování řádků i sloupců od 1.
		'''

		return self.kb_shm.dataAt(line, col)


	def get_data_for(self, line, col_name, col_name_type=None, separator = None):
		'''
		Číslování řádků od 1.
		'''

		data = self.kb_shm.dataFor(line, col_name, col_name_type)
		if data is None:
			_, all_about_entity = self.get_complete_ent_pretty(line)
			print_dbg_en(all_about_entity)
		if separator:
			data = data.split(separator) if data else []
		return data


	def get_head_at(self, line, col):
		'''
		Číslování řádků i sloupců od 1.
		'''

		return self.kb_shm.headAt(line, col)


	def get_head_for(self, ent_type_set, col):
		'''
		Číslování sloupců od 1.
		'''

		return self.kb_shm.headFor(ent_type_set, col)


	def get_head_col(self, ent_type_set, col_name, col_name_type=None):
		'''
		Vrátí číslo sloupce pro požadovaný ent_type_set a jméno sloupce.
		'''

		return self.kb_shm.headCol(ent_type_set, col_name, col_name_type)


	def get_complete_data(self, line):
		'''
		Vrátí seznam sloupců na řádku \a line, tak jak je v KB.
		'''

		col = 1
		result = []
		column_data = self.get_data_at(line, col)

		while column_data != None:
			result.append(column_data)
			column_data = self.get_data_at(line, col)
			col += 1

		return result


	def get_complete_head(self, ent_type_set):
		'''
		Vrátí seznam hlaviček sloupců pro uspořádanou množinu typů \a ent_type_set.
		'''

		col = 1
		result = []
		column_head = self.get_head_for(ent_type_set, col)

		while column_head != None:
			result.append(column_head)
			column_head = self.get_head_for(ent_type_set, col)
			col += 1

		return result

	def get_complete_ent_pretty(self, line):
		'''
		Vrátí tuple (počet sloupců, celý řádek), kde v jednom řetězci je celý řádek pro požadovaný line, tak jak je v KB.
		Parametr delim umožňuje změnit oddělovač sloupců.
		'''

		ent_type_set = self.get_ent_type(line)
		column_head_list = self.get_complete_head(ent_type_set)
		column_data_list = self.get_complete_data(line)

		column_repr_list = []
		for column_head, column_data in itertools.izip_longest(column_head_list, column_data_list):
			column_repr_list.append("%s: %s" % (column_head and column_head.name, column_data))

		return len(column_repr_list), "\n".join(column_repr_list)


	def get_ent_type(self, line):
		"""
		Returns an type of an entity at the line of the knowledge base represent as an ordered set of type
		"""

		return self.kb_shm.dataType(line)


	def get_dates(self, line):
		ent_type_set = self.get_ent_type(line)
		if 'person' in ent_type_set:
			dates = set([self.get_data_for(line, "DATE OF BIRTH"), self.get_data_for(line, "DATE OF DEATH")])
			dates.discard("")
			return dates
		return set()


	def get_location_code(self, line):
		return self.get_data_for(line, "FEATURE CODE")[0:3]


	def get_nationalities(self, line):
		ent_type_set = self.get_ent_type(line)
		if "nationality" in ent_type_set:
			nation = self.get_data_for(line, "ALIASES", separator = KB_MULTIVALUE_DELIM)
			# nation.extend(self.get_data_for(line, "ADJECTIVAL FORM").split(KB_MULTIVALUE_DELIM)) # NOT present in GKB
			nation.append(self.get_data_for(line, "NAME"))
			nation.append(self.get_data_for(line, "DISAMBIGUATION NAME"))
			nation.append(self.get_data_for(line, "SHORT NAME"))
			nation.append(self.get_data_for(line, "COUNTRY NAME"))
		elif "person" in ent_type_set:
			nation = self.get_data_for(line, "NATIONALITIES", separator = KB_MULTIVALUE_DELIM)
		nation = set([nat.lower() for nat in nation if nat != ""])
		return nation

	def get_uri(self, line):
		result = self.get_data_for(line, "WIKIDATA URL") or self.get_data_for(line, "WIKIPEDIA URL") or self.get_data_for(line, "DBPEDIA URL")
		return result

	def get_score(self, line):
		'''
		Returns disambiguation score based on Wikipedia statistics and score based on other metrics.
		'''

		result = self.get_data_for(line, "CONFIDENCE")

		try:
			return float(result)
		except:
			err_type_set = self.get_ent_type(line)
			err_head = self.get_complete_head(err_type_set)
			err_data = self.get_complete_data(line)
			print_dbg_en("Line \"", line, "\" have non-integer type \"", type(result), "\" with content \"", result, "\"", delim="")
			print_dbg_en("Dump head for type \"", repr(err_type_set), "\" (cols=", len(err_head), "):\n\"\"\"\n", "\t".join(h.name for h in err_head), "\n\"\"\"", delim="")
			print_dbg_en("Dump line \"", line, "\" (cols=", len(err_data), "):\n\"\"\"\n", "\t".join(err_data), "\n\"\"\"", delim="")
			print_dbg_en("Version of connected KB (at \"", self.kb_shm_name, "\") is \"", self.version(), "\".", delim="")
			raise


	def people_named(self, subname):
		'''
		Returns all names (KB ids) containing a given subname.
		'''

		return self.name_dict.get(subname, set())
