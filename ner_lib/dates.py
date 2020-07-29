#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright 2014 Brno University of Technology

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

# Author: Jan Doležal, idolezal[at]fit.vutbr.cz

# meta version

# ====== IMPORTY ======

import re
import os
import importlib

# ====== GLOBÁLNÍ KONSTANTY ======
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ====== GLOBÁLNÍ PROMĚNNÉ ======

# ====== FUNKCE A TŘÍDY ======

class ISO_date(object):
	'''
	Třída uchovávající datum (tedy rok, měsíc a den).
	Obsahuje atributy day, month a year.
	'''
	def __init__(self, year=0, month=0, day=0):
		'''
		Inicializace.
		:type year: **int**
		:type month: **int**
		:type day: **int**
		'''
		self.year = year
		self.month = month
		self.day = day
	
	def __str__(self):
		'''
		Převede self na řetězec ve formátu ISO 8601 (např. 2013-07-16).
		:returns:  str -- Vrací datum ve formátu ISO 8601.
		'''
		year = str(self.year).zfill(4)
		month = str(self.month).zfill(2)
		day = str(self.day).zfill(2)
		
		return "%s-%s-%s" % (year, month, day)
	
	def showWithoutZeros(self):
		'''
		Převede self na řetězec ve formátu ISO 8601 a případně odstraní nulový den a měsíc (např. 2013-07).
		:returns:  str -- Vrací datum ve formátu ISO 8601.
		'''
		year = str(self.year).zfill(4)
		month = ""
		day = ""
		
		if self.month:
			month = "-" + str(self.month).zfill(2)
			if self.day:
				day = "-" + str(self.day).zfill(2)
		
		return "".join((year, month, day))
	
	def from_isostr(self, input_str):
		'''
		Inicializace z řetězce (např. 2013-07-16).
		'''
		if (input_str == None) or (input_str == ""):
			self.year = 0
			self.month = 0
			self.day = 0
			return
		
		numbers = input_str.split("-")
		if len(numbers) > 0:
			self.year = int(numbers[0])
			if len(numbers) > 1:
				self.month = int(numbers[1])
				if len(numbers) > 2:
					self.day = int(numbers[2])
				else:
					self.day = 0
			else:
				self.month = 0
				self.day = 0
	
	def is_empty(self):
		'''
		Vrací True, pokud všechny hodnoty obsahují nulu.
		'''
		if (self.year == 0) and (self.month == 0) and (self.day == 0):
			return True
		return False
#

class Date(object):
	'''
	Třída pro nalezená data. Kromě roku, měsíce a dnu obsahuje také místo nalezení ve zdrojovém řetězci
	a řetězec, ze kterého bylo toto datum převedeno.
	
	Po vytvoření nové instance je nutné zavolat init_date() nebo init_interval() pro inicializaci atributů.
	'''
	regex_split_interval = None
	long_interval_delim = NotImplemented
	
	class Type:
		NONE=-1
		DATE=0
		INTERVAL=1
	
	def __init__(self):
		self.class_type = self.Type.NONE # Atribut značící typ nalezeného data (prosté datum či interval).
		pass
	
	def init_date(self, source, iso8601, start_offset=0, confidence=100):
		'''
		Inicializace data.
		:type source: **unicode**
		:type iso8601: **ISO_date**
		:type start_offset: **int**
		:type confidence: **int**
		'''
		self.class_type = self.Type.DATE
		
		self.source = source     # Řetězec source ze zdrojového textu
		self.iso8601 = iso8601   # Datum v **ISO_date**
		self.start_offset = start_offset # Začátek řetězce source ve zdrojovém textu
		self.end_offset = start_offset + len(source) # Konec řetězce source ve zdrojovém textu
		self.confidence = confidence # Míra spolehlivosti informace
	
	def init_interval(self, source, date_from, date_to, start_offset=0, confidence=100):
		'''
		Inicializace datového intervalu.
		:type source: **unicode**
		:type date_from: **ISO_date**
		:type date_to: **ISO_date**
		:type start_offset: **int**
		:type confidence: **int**
		'''
		self.class_type = self.Type.INTERVAL
		
		self.source = source
		self.date_from = date_from # Počáteční datum v **ISO_date**
		self.date_to = date_to     # Koncové datum v **ISO_date**
		self.start_offset = start_offset
		self.end_offset = start_offset + len(source)
		self.confidence = confidence
	
	def split_interval(self):
		'''
		Rozdělí interval do dvou datumů, které vrátí v list().
		'''
		if (self.class_type == self.Type.INTERVAL):
			if not self.__class__.regex_split_interval:
				self.__class__.regex_split_interval = re.compile("(?i)[ ]*"+self.__class__.long_interval_delim+"[ ]*")
			match = self.__class__.regex_split_interval.search(self.source)
			date_from = Date()
			date_from.init_date( self.source[:match.start()], self.date_from, self.start_offset, self.confidence )
			date_to = Date()
			date_to.init_date( self.source[match.start()+len(match.group()):], self.date_to, self.start_offset+( match.start()+len(match.group()) ), self.confidence )
			return [date_from, date_to]
		else:
			return [self]
	
	def __str__(self):
		'''
		Převede atributy self na řetězec pro testovací výpisy.
		:returns: str -- Vrací řetězec pro testovací výpisy.
		'''
		result = ""
		
		if self.class_type == self.Type.DATE:
			result = map(str, (self.start_offset, self.end_offset, "date", self.source, self.iso8601))
			result = "\t".join(result)
		elif self.class_type == self.Type.INTERVAL:
			result = map(str, (self.start_offset, self.end_offset, "interval", self.source))
			result = "%s\t%s -- %s" % ("\t".join(result), self.date_from, self.date_to)
		else:
			result = "class_type: NONE"
		
		return result
#

def importLanguageModule(language):
	return importlib.import_module(f".lang_modules.{language}.dates", __package__)

# konec souboru dates.py
