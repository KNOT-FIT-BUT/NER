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

# EN version

import sys
import re
import dateutil.parser as dparser

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
			if not Date.regex_split_interval:
				Date.regex_split_interval = re.compile("(?i)[ ]*"+long_interval_delim+"[ ]*")
			match = Date.regex_split_interval.search(self.source)
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
		:returns:  str -- Vrací řetězec pro testovací výpisy.
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

def addRegexParentheses(iterable):
	'''
	Přidá non-grouping verzi regulárních závorek na každou položku.
	'''
	for item in iterable:
		yield f"(?:{item})"
#

MAX_ONLY_YEAR = 2999
dash_or_hyphen = '-\u2010\u2011\u2012\u2013\u2012\u2013\u2014\u2015\u2043'

months = [
	"Jan(?:uary)?",
	"Feb(?:ruary)?",
	"Mar(?:ch)?",
	"Apr(?:il)?",
	"May",
	"Jun(?:e)?",
	"Jul(?:y)?",
	"Aug(?:ust)?",
	"Sep(?:t(?:ember)?)?",
	"Oct(?:ober)?",
	"Nov(?:ember)?",
	"Dec(?:ember)?"
]

months = addRegexParentheses(months)
allMonthsOR = "(?:"+"|".join(months)+")"

int2nth = {
	1:"first", 2:"second", 3:"third", 4:"fourth", 5:"fifth", 6:"sixth", 7:"seventh", 8:"eighth", 9:"nineth", 10:"tenth", 
	11:"eleventh", 12:"twelfth", 13:"thirteenth", 14:"fourteenth", 15:"fifteenth", 16:"sixteenth", 17:"seventeenth", 18:"eighteenth",
	19:"nineteenth", 20:"twentieth", 21:"twenty-first", 22:"twenty-second", 23:"twenty-third", 24:"twenty-fourth", 25:"twenty-fifth",
	26:"twenty-sixth", 27:"twenty-seventh", 28:"twenty-eighth", 29:"twenty-nineth", 30:"thirtieth", 31:"thirty-first"
}

nth2int = dict(zip(int2nth.values(), int2nth.keys()))

allNthOR = nth2int.keys()
allNthOR = addRegexParentheses(allNthOR)
allNthOR = "(?:"+"|".join(allNthOR)+")"

delim = "(?:[/_\-\\\]|["+dash_or_hyphen+"])"
long_interval_delim = "(?:["+dash_or_hyphen+"]|(?:[ ]to[ ]))"
desh_or_hypen_or_space_delim = "(?:(?:[ ]*["+dash_or_hyphen+"][ ]*)|[ ]+)"

url_char = "(?:\w|\d|[-._~!$&'()*+,;=:/?#\\[\\]%])"

start_delim = "(?:^|\W)"
end_delim = "(?:$|\W)"
not_start_delim = "(?<!\w[$/-_])"
not_end_delim = "(?![$/_%]\w)"
anno_domini = "(?:(?:[ ]+(?:AD|A\.D\.))|(?![ ]+(?:BC|B\.C\.)"+end_delim+"))"

# regulární výrazy pro match datumů
patterns = [
	# intervaly
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "["+dash_or_hyphen+"]" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # June 6-Sept. 23, 2007
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "["+dash_or_hyphen+"]" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # Aug. 4-31, 2007
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # June. 6, 2005 – Sept. 12, 2007
	"\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}", # 20 March, 1856 – 10 January 1941
	# intervaly ((den\?, měsíc\?, rok) a (den\?, měsíc, rok)) a ((den\?, měsíc, rok) a (den\?, měsíc\?, rok))
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{4}", # 1856 - April 2, 1918
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # Mar. 30, 1853 - 1888
	"(?:(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}", # March, 1856 - 1941; March, 1856 – January 1941
	"(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "(?:(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}", # 1856 – January 1941; 1740 - 10 February 1808
	# datumy
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # Sept. 12, 2007
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[ ]+" + "[']\d{2}", # Jul 18 '10
	"\d\d\d\d["+dash_or_hyphen+"]\d\d["+dash_or_hyphen+"]\d\d", # 1999-12-28
	"\d\d?"+delim+"\d\d?"+delim+"\d{3,4}", # 12-11-1694, 12/11/1694
	"\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}", # 12.11.1694, 12. 11. 1694
	"\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}", # 12th Nov. 1694; 8th of November 2003; 27 May, 1859
	# Pouze měsíc a rok:
	allMonthsOR + "[.]?[ ]+" + "\d{4}", # November 2003
	# Speciální fuzzy slovní formáty:
	"mid" + "[ ]*["+dash_or_hyphen+"][ ]*" + "\d{4}[s]?", # "mid-1980s" => "1985-01-01 -- 1985-12-31"
	"mid" + "[ ]*["+dash_or_hyphen+"][ ]*" + "\d{1,2}(?:th|st|rd|nd)?" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "mid-19th century" => "1801-01-01 -- 1850-12-31"
	"\d{1,2}(?:th|st|rd|nd)?" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "17th-century", "4th century AD" # "15th century" => "1401-01-01 -- 1500-12-31"
	allNthOR + desh_or_hypen_or_space_delim + "century" + anno_domini, # "fourth-century" => "0301-01-01 -- 0400-12-31"
	# Pouze rok:
	"\d\d\d\d-\d\d", # 1694-99
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # 1693-1734, 1693 to 1734
	"\d{4}[s]?", # 1694, 1690s
]

patterns = addRegexParentheses(patterns)
allPatternsOR = "(?i)"+start_delim+not_start_delim+"("+"|".join(patterns)+")"+not_end_delim+"(?="+end_delim+")"
#allPatternsOR = u"(?i)(?:^|(?<!\w[$€/-_:]))("+"|".join(patterns)+")(?:(?=$)|(?![$€°/_%]\w))"
# konec: regulární výrazy pro match datumů

# regulární výrazy pro rozpoznání intervalů
intervals = [
	"("+allMonthsOR + "[.]?[ ]+" + "\d\d?" + ")["+dash_or_hyphen+"](" + allMonthsOR + "[.]?[ ]+" + "\d\d?)" + "[,][ ]+" + "\d{3,4}", # June 6-Sept. 23, 2007
	allMonthsOR + "[.]?[ ]+" + "(\d\d?" + ")["+dash_or_hyphen+"](" + "\d\d?)" + "[,][ ]+" + "\d{3,4}", # Aug. 4-31, 2007
	"("+allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4})", # June. 6, 2005 – Sept. 12, 2007
	"(\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + "\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4})", # 20 March, 1856 – 10 January 1941
]
intervalsPartialDates = [
	# intervaly ((den\?, měsíc\?, rok) a (den\?, měsíc, rok)) a ((den\?, měsíc, rok) a (den\?, měsíc\?, rok))
	"(" + "\d{4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{4})", # 1856 - April 2, 1918
	"("+allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + "\d{4})", # Mar. 30, 1853 - 1888
	"("+"(?:(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + "(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}"+")", # March, 1856 - 1941; March, 1856 – January 1941
	"("+"(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}" + ")[ ]*"+long_interval_delim+"[ ]*(" + "(?:(?:\d\d?" + "(?:th|st|rd|nd)?" + "[ ]+(?:of[ ]+)?)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}"+")", # 1856 – January 1941; 1740 - 10 February 1808
]
intervalsOnlyYears = [
	# Pouze rok:
	"\d\d(\d\d)["+dash_or_hyphen+"](\d\d)", # 1694-99
	"(\d{4})" + "[ ]*"+long_interval_delim+"[ ]*" + "(\d{4})", # 1693-1734, 1693 to 1734
]
intervals += intervalsPartialDates + intervalsOnlyYears

intervals = addRegexParentheses(intervals)
allIntervalsOR = "(?:"+"|".join(intervals)+")"

intervalsOnlyYears = addRegexParentheses(intervalsOnlyYears)
allIntervalsOnlyYearsOR = "(?:"+"|".join(intervalsOnlyYears)+")"
# konec: regulární výrazy pro rozpoznání intervalů

# regulární výrazy pro rozpoznání datumů s nižším confidence
unsureDates = [
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[ ]+" + "[']\d{2}", # Jul 18 '10
	"\d\d?"+delim+"\d\d?"+delim+"\d{3,4}", # 12-11-1694, 12/11/1694
	"\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}", # 12.11.1694, 12. 11. 1694
	"\d\d\d\d-\d\d", # 1694-99
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # 1693-1734, 1693 to 1734
	"\d{4}", # 1694
]

unsureDates = addRegexParentheses(unsureDates)
allUnsureDatesOR = "(?:"+"|".join(unsureDates)+")"
# konec: regulární výrazy pro rozpoznání datumů s nižším confidence

# regulární výrazy pro rozpoznání speciálních fuzzy slovních formátů
specIntervals = {
	"midDecade": "mid" + "[ ]*["+dash_or_hyphen+"][ ]*" + "(\d{3}0)s", # "mid-1980s" => "1985-01-01 -- 1985-12-31"
	"midYear": "mid" + "[ ]*["+dash_or_hyphen+"][ ]*" + "(\d{4})[s]?", # "mid-1987" => "1987-06-01 -- 1987-06-30"
	"midCentury": "mid" + "[ ]*["+dash_or_hyphen+"][ ]*" + "(\d{1,2})(?:th|st|rd|nd)?" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "mid-19th century" => "1801-01-01 -- 1850-12-31"
	"century": "(\d{1,2})(?:th|st|rd|nd)?" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "17th-century", "4th century AD" # "15th century" => "1401-01-01 -- 1500-12-31"
	"nthCentury": "("+allNthOR+")" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "fourth-century" => "0301-01-01 -- 0400-12-31"
}

for regex in specIntervals:
	specIntervals[regex] = re.compile("(?i)^(?:"+specIntervals[regex]+")$")

def specIntervalsMatch(text):
	result = {}
	for regex in specIntervals:
		result[regex] = specIntervals[regex].match(text)
	return result

# konec: regulární výrazy pro rozpoznání speciálních fuzzy slovních formátů

def find_dates(text, split_interval=True):
	'''
	Nalezne datumy v řetězci předaném pomocí parametru text.
	:param text: Řetězec se zdrojovými daty.
	:type text: **unicode**
	:param split_interval: Pokud je True, všechny intervaly se rozpadnou na dva datumy.
	:type split_interval: **bool**
	:returns:  list -- Vrací list všech nalezených datumů.
	'''
	assert isinstance(text, str)
	assert isinstance(split_interval, bool)
	
	regexIntervals = re.compile("(?i)^"+allIntervalsOR+"$")
	regexUnsureDates = re.compile("(?i)^"+allUnsureDatesOR+"$")
	dates = []
	
	for match in re.finditer(allPatternsOR, text):
		string = match.group(1)
		
		isUnsure = bool( regexUnsureDates.search(string) )
		isInterval = bool( regexIntervals.search(string) )
		specialInterval = specIntervalsMatch(string)
		isSpecial = any(specialInterval.values())
		
		# úprava pro parser
		string = re.sub("(?i)Sept([. ])", "Sep\\1", string)
		string = re.sub("(?i)^(\d{4})[s]$", "\\1", string)
		
		if isInterval:
			interval = regexIntervals.match(string)
			
			i = 0
			interval_groups = interval.groups()
			while i < len(interval_groups):
				if interval_groups[i] != None:
					break
				i = i + 1
			
			string_from = string[:interval.end(i+1)] + string[interval.end(i+2):]
			string_to = string[:interval.start(i+1)] + string[interval.start(i+2):]
			
			try:
				date_from = dparser.parse(string_from)
				date_to = dparser.parse(string_to)
				
				if re.search("(?i)^\d{3,4}$", string_from):
					ISO_from = ISO_date(date_from.year)
				else:
					if re.search("(?i)^"+allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}$", string_from):
						ISO_from = ISO_date(date_from.year, date_from.month)
					else:
						ISO_from = ISO_date(date_from.year, date_from.month, date_from.day)
				
				if re.search("(?i)^\d{3,4}$", string_to):
					ISO_to = ISO_date(date_to.year)
				else:
					if re.search("(?i)^"+allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}$", string_to):
						ISO_to = ISO_date(date_to.year, date_to.month)
					else:
						ISO_to = ISO_date(date_to.year, date_to.month, date_to.day)
			except ValueError:
				continue # nesprávné formáty datumů se nebudou brát
		elif isSpecial:
			# "mid-1980s" => "1985-01-01 -- 1985-12-31"
			if specialInterval["midDecade"]:
				special = specialInterval["midDecade"]
				special = int(special.group(1)) + 5
				ISO_from = ISO_date( special, 1, 1 )
				ISO_to = ISO_date( special, 12, 31 )
			
			# "mid-1987" => "1987-06-01 -- 1987-06-30"
			elif specialInterval["midYear"]:
				special = specialInterval["midYear"]
				special = int(special.group(1))
				ISO_from = ISO_date( special, 6, 1 )
				ISO_to = ISO_date( special, 6, 30 )
			
			# "mid-19th century" => "1801-01-01 -- 1850-12-31"
			elif specialInterval["midCentury"]:
				special = specialInterval["midCentury"]
				special = ( int(special.group(1)) - 1 ) * 100
				special_from = special + 1
				special_to = special + 50
				ISO_from = ISO_date( special_from, 1, 1 )
				ISO_to = ISO_date( special_to, 12, 31 )
			
			# "15th century" => "1401-01-01 -- 1500-12-31"
			elif specialInterval["century"]:
				special = specialInterval["century"]
				special = ( int(special.group(1)) - 1 ) * 100
				special_from = special + 1
				special_to = special + 100
				ISO_from = ISO_date( special_from, 1, 1 )
				ISO_to = ISO_date( special_to, 12, 31 )
			
			# "fourth-century" => "0301-01-01 -- 0400-12-31"
			elif specialInterval["nthCentury"]:
				special = specialInterval["nthCentury"]
				special = nth2int[special.group(1).lower()]
				special = ( special - 1 ) * 100
				special_from = special + 1
				special_to = special + 100
				ISO_from = ISO_date( special_from, 1, 1 )
				ISO_to = ISO_date( special_to, 12, 31 )
			else:
				raise RuntimeError("Chybna implementace!")
		else:
			isOnlyYear = bool( re.search("(?i)^\d{3,4}$", string) )
			if isOnlyYear:
				if re.search("(?i)^[0]{1,4}$", string) or int(string) > MAX_ONLY_YEAR:
					continue # pokud bude rok jen z nul nebo bude větší než MAX_ONLY_YEAR, pak se takové datum neukládá
				ISO = ISO_date( int(string) )
			else:
				try:
					date = dparser.parse(string)
					# Pokud je znám pouze rok a měsíc, pak se za den doplní nula
					if re.search("(?i)^"+allMonthsOR + "[.]?[ ]+" + "\d{3,4}$", string):
						ISO = ISO_date(date.year, date.month)
					else:
						ISO = ISO_date(date.year, date.month, date.day)
				except ValueError:
					continue # nesprávné formáty datumů se nebudou brát
		
		# Získané datum se uloží do třídy Date
		date = Date()
		
		if isUnsure:
			confidence = 80
		else:
			confidence = 100
		
		if isInterval or isSpecial:
			date.init_interval( match.group(1), ISO_from, ISO_to, match.start(1), confidence )
		else:
			date.init_date( match.group(1), ISO, match.start(1), confidence )
		
		# Zpracované datum se přidá do seznamu
		if split_interval and not isSpecial:
			dates += date.split_interval()
		else:
			dates += [date]
	
	return dates

# TEST
if __name__ == '__main__':
	delimiter = "-"*33
	text = sys.stdin.read()
	result = find_dates(text)
	#result = find_dates(text, False)
	for item in result:
		print( delimiter + "\n" + str(item) )
	pass

# konec souboru dates.py
