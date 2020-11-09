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
# Modified by: Tomáš Volf, ivolf[at]fit.vutbr.cz

# CZ version

import sys
import re
import dateutil.parser as dparser

# <LOKÁLNÍ IMPORTY>
from ...dates import ISO_date, Date as MetaDate
# </LOKÁLNÍ IMPORTY>

def addRegexParentheses(list):
	'''
	Přidá non-grouping verzi regulárních závorek na každou položku listu *IN PLACE*.
	'''
	i = 0
	while i < len(list):
		list[i] = "(?:"+list[i]+")"
		i = i + 1
#

MAX_ONLY_YEAR = 2999
dash_or_hyphen = '-\u2010\u2011\u2012\u2013\u2012\u2013\u2014\u2015\u2043'

months = [
	"led(?:(?:na)|(?:en))?",
	"úno(?:(?:ra)|(?:r))?",
	"bře(?:(?:zen)|(?:zna))?",
	"dub(?:(?:en)|(?:na))?",
	"kvě(?:(?:ten)|(?:tna))?",
	"červenec",
	"července",
	"čer(?:(?:ven)|(?:vna))?",
	"čec",
	"srp(?:(?:en)|(?:na))?",
	"zář(?:í)?",
	"říj(?:(?:en)|(?:na))?",
	"lis(?:(?:topadu)|(?:topad))?",
	"pro(?:(?:sinec)|(?:since))?"
]

addRegexParentheses(months)
allMonthsOR = "(?:"+"|".join(months)+")"

mnt2int = {
	"01" : ["led", "leden", "ledna"],
	"02" : ["úno", "únor", "února"],
	"03" : ["bře", "březen", "března"],
	"04" : ["dub", "duben", "dubna"],
	"05" : ["kvě", "květen", "května"],
	"06" : ["čer", "červen", "června"],
	"07" : ["červenec", "července", "čec"],
	"08" : ["srp", "srpen", "srpna"],
	"09" : ["zář", "září"],
	"10" : ["říj", "říjen", "října"],
	"11" : ["lis", "listopad", "listopadu"],
	"12" : ["pro", "prosinec", "prosince"],
}

delim = "(?:[/_\-\\\]|["+dash_or_hyphen+"])"
long_interval_delim = "(?:["+dash_or_hyphen+"]|(?:[ ]do[ ]))"
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
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # June. 6, 2005 – Sept. 12, 2007
	"\d\d?" + "[.]?" + "[ ]+" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d\d?" + "[.]?" + "[ ]+" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}", # 20 March, 1856 – 10 January 1941
	# intervaly ((den\?, měsíc\?, rok) a (den\?, měsíc, rok)) a ((den\?, měsíc, rok) a (den\?, měsíc\?, rok))
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d\d?" + "[.]?" + "[ ]+" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}", # 1856 - 20 March, 1856
	"\d\d?" + "[.]?" + "[ ]+" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # Mar. 30, 1853 - 1888
	"(?:(?:\d\d?" + "[.]?" + "[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "(?:\d\d?" + "[.]?" + "[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}", # March, 1856 - 1941; March, 1856 – January 1941
	"(?:\d\d?" + "[.]?" + "[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + "\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "(?:(?:\d\d?" + "[.]?" + "[ ]+)?" + allMonthsOR + "[.]?[,]?[ ]+" + ")?\d{4}", # 1856 – January 1941; 1740 - 10 February 1808
	"\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}",
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # 1693-1734, 1693 to 1734
	# datumy
	allMonthsOR + "[.]?[ ]+" + "\d\d?" + "[,][ ]+" + "\d{3,4}", # lis. 12, 2007
	"\d\d\d\d["+dash_or_hyphen+"]\d\d["+dash_or_hyphen+"]\d\d", # 1999-12-28
	"\d\d\d\d[-]?\s*" + allMonthsOR + "[-]?\s*\d\d", # 2010 listopad 16
	"\d\d?"+delim+"\d\d?"+delim+"\d{3,4}", # 12-11-1694, 12/11/1694
	"\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}", # 12.11.1694, 12. 11. 1694
	"\d\d?" + "[.]?[ ]+" + allMonthsOR + "[.]?[ ]+" + "\d{3,4}", # 16. listopadu 2003
	# Pouze měsíc a rok:
	allMonthsOR + "[.]?[ ]+" + "\d{4}", # November 2003
	# Speciální fuzzy slovní formáty:
	#"\d{1,2}(?:th|st|rd|nd)?" + desh_or_hypen_or_space_delim + "century" + anno_domini, # "17th-century", "4th century AD" # "15th century" => "1401-01-01 -- 1500-12-31"
	#allNthOR + desh_or_hypen_or_space_delim + "century" + anno_domini, # "fourth-century" => "0301-01-01 -- 0400-12-31"
	# Pouze rok:
	"\d\d\d\d", # 1694-99
	"\d{4}[s]?", # 1694, 1690s
]

addRegexParentheses(patterns)
allPatternsOR = "(?i)"+start_delim+not_start_delim+"("+"|".join(patterns)+")"+not_end_delim+"(?="+end_delim+")"
#allPatternsOR = "(?i)(?:^|(?<!\w[$€/-_:]))("+"|".join(patterns)+")(?:(?=$)|(?![$€°/_%]\w))"
# konec: regulární výrazy pro match datumů

# regulární výrazy pro rozpoznání datumů s nižším confidence
unsureDates = [
	"\d\d?"+delim+"\d\d?"+delim+"\d{3,4}", # 12-11-1694, 12/11/1694
	"\d\d?" + "[.][ ]*" + "\d\d?" + "[.][ ]*" + "\d{3,4}", # 12.11.1694, 12. 11. 1694
	"\d\d\d\d-\d\d", # 1694-99
	"\d{4}" + "[ ]*"+long_interval_delim+"[ ]*" + "\d{4}", # 1693-1734, 1693 to 1734
	"\d{4}", # 1694
]

addRegexParentheses(unsureDates)
allUnsureDatesOR = "(?:"+"|".join(unsureDates)+")"
# konec: regulární výrazy pro rozpoznání datumů s nižším confidence

def not_czech_form(month, string):

	try:
		int(string[:4])
		return True
	except Exception:
		if string.startswith(month):
			return True

		return False

def get_date(string):
	isOnlyYear = bool( re.search("(?i)^\d{3,4}$", string) )
	if isOnlyYear:
		ISO = ISO_date( int(string) )
	else:
		dayfirst= True
		month = re.search(allMonthsOR, string)
		if month:
			month = month.group()
			month_number = None
			for key in mnt2int:
				if month in mnt2int[key]:
					month_number = key
					break
			if not_czech_form(month, string):
				dayfirst = False
			string = string.replace(month, month_number)

		try:
			date = dparser.parse(string, dayfirst=dayfirst)
			# Pokud je znám pouze rok a měsíc, pak se za den doplní nula
			if re.search("(?i)^\d\d[.]?[ ]+" + "\d{3,4}$", string):
				ISO = ISO_date(date.year, date.month)
			else:
				ISO = ISO_date(date.year, date.month, date.day)
		except ValueError:
			return None # nesprávné formáty datumů se nebudou brát

	return ISO

# konec: regulární výrazy pro rozpoznání speciálních fuzzy slovních formátů

class Date(MetaDate):
	long_interval_delim = long_interval_delim
#

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
	

	regexIntervals = re.compile("[ ]*"+long_interval_delim+"[ ]*")
	regexUnsureDates = re.compile("(?i)^"+allUnsureDatesOR+"$")
	dates = []
	
	for match in re.finditer(allPatternsOR, text):
		string = match.group(1)
		
		isUnsure = bool( regexUnsureDates.search(string) )	
		isInterval = bool( regexIntervals.search(string) )
		if len(re.findall("[" + dash_or_hyphen + "]", string)) > 1:
			isInterval = False
		
		if isInterval:
			interval = regexIntervals.split( string )
			string_from= interval[0]
			string_to= interval[1]

			ISO_from = get_date(string_from)
			ISO_to = get_date(string_to)
			
			if not ISO_from or not ISO_to:
				continue
		else:
			ISO = get_date(string)
			if not ISO:
				continue

		# Získané datum se uloží do třídy Date
		date = Date()
		
		if isUnsure:
			confidence = 80
		else:
			confidence = 100
		
		if isInterval:
			date.init_interval( match.group(1), ISO_from, ISO_to, match.start(1), confidence )
		else:
			date.init_date( match.group(1), ISO, match.start(1), confidence )
		
		# Zpracované datum se přidá do seznamu
		if split_interval:
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
