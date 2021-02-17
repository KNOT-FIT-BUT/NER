#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vutbr.cz
#
# Description: Creates namelist from KB.

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import argparse
import gc
import itertools
import pickle
import regex

from multiprocessing import Pool

import metrics_knowledge_base

from configs import LANG_DEFAULT
from libs.automata_variants import AutomataVariants
from libs.entities.entity_loader import EntityLoader
from libs.module_loader import ModuleLoader
from libs.utils import remove_accent

# a dictionary for storing results
dictionary = {}
# word frequency for variants with first lower- and first upper- case letter
word_freq = dict()

# multiple values delimiter
KB_MULTIVALUE_DELIM = metrics_knowledge_base.KB_MULTIVALUE_DELIM

URI_COLUMN_NAMES = ['WIKIPEDIA URL', 'WIKIDATA URL', 'DBPEDIA URL']

# defining commandline arguments
parser = argparse.ArgumentParser()
parser.add_argument('-l', '--lang', type = str, required = True, help = 'language to process')
parser.add_argument('-d', '--lowercase', action = 'store_true', help = 'creates a lowercase list')
parser.add_argument('-a', '--autocomplete', action = 'store_true', help = 'creates a list for autocomplete')
parser.add_argument('-u', '--uri', action = 'store_true', help = 'creates an uri list')
parser.add_argument('-t', '--taggednames', required = True, help = 'file path of inflected tagged names (suitable for debug)')
parser.add_argument('-k', '--kb', required = True, help = 'knowledgebase file path')
parser.add_argument('-I', '--indir', help = 'directory base for auxiliary input files')
parser.add_argument('-O', '--outdir', default = '.', help = 'directory base cached / temporary / output files')
parser.add_argument('-c', '--clean-cached', action = 'store_true', help = 'do not use previously created cached files')
parser.add_argument('-n', '--processes', type = int, default = 4, help = 'numer of processes for multiprocessing pool.')
args = parser.parse_args()

CACHED_SUBNAMES = 'cached_subnames.pkl'
CACHED_INFLECTEDNAMES = 'cached_inflectednames.pkl'

if not args.indir or not os.path.isdir(args.indir):
	args.indir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'inputs/{}'.format(args.lang))

# automata variants config
atm_config = AutomataVariants.DEFAULT
if args.lowercase:
	atm_config |= AutomataVariants.LOWERCASE
if args.autocomplete:
	# different format - can not be combined with other types
	atm_config = AutomataVariants.NONACCENT

# load KB struct
kb_struct = metrics_knowledge_base.KnowledgeBase(args.lang, args.kb)
namelist = ModuleLoader.load('namelist', args.lang, 'Namelist', '..dictionaries')
namelist.setKBStruct(kb_struct)
namelist.setAutomataVariants(atm_config)
# load laguage specific class of Persons entity
persons = EntityLoader.load('persons', args.lang, 'Persons')

SURNAME_MATCH = regex.compile(r"(((?<=^)|(?<=[ ]))(?:(?:da|von)(?:#[^ ]+)? )?((?:\p{Lu}\p{Ll}*(?:#[^- ]+)?-)?(?:\p{Lu}\p{Ll}+(?:#[^- ]+)?))$)")
UNWANTED_MATCH = namelist.reUnwantedMatch()


def pickle_load(fpath):
	with open(fpath, 'rb') as f:
		return pickle.load(f)

def pickle_dump(data, fpath):
	with open(fpath, 'wb') as f:
		pickle.dump(data, f)


''' For firstnames or surnames it creates subnames of each separate name and also all names together '''
def get_subnames_from_parts(subname_parts):
	subnames = set()
	subname_all = ''
	for subname_part in subname_parts:
		subname_part = regex.sub(r'#[A-Za-z0-9]E?( |-|–|$)', '\g<1>', subname_part)
		subnames.add(subname_part)
		if subname_all:
			subname_part = ' ' + subname_part
		subname_all += subname_part

	if (subname_all):
		subnames.add(subname_all)
	return subnames


def build_name_variant(ent_flag, strip_nameflags, inflection_parts, is_basic_form, i_inflection_part, stacked_name, name_inflections):
	subnames = set()
	separator = ''
	if i_inflection_part < len(inflection_parts):
		for inflected_part in inflection_parts[i_inflection_part]:
			if stacked_name and inflected_part:
				separator = ' '
			name_inflections, built_subnames = build_name_variant(ent_flag, strip_nameflags, inflection_parts, is_basic_form, i_inflection_part + 1, stacked_name + separator + inflected_part, name_inflections)
			subnames |= built_subnames
	else:
		new_name_inflections = set()
		new_name_inflections.add(stacked_name)

		if ent_flag in ['F', 'M']:
			match_one_firstname_surnames = regex.match("^([^#]+#[G]E? )(?:[^#]+#[G]E? )+((?:[^# ]+#SE?(?: \p{L}+#[L78]E?)*(?: |$))+)", stacked_name)
			if match_one_firstname_surnames:
				firstname_surnames = match_one_firstname_surnames.group(1) + match_one_firstname_surnames.group(2)
				if firstname_surnames not in name_inflections:
					new_name_inflections.add(firstname_surnames)

			if is_basic_form:
				firstnames_surnames = regex.match("^((?:[^#]+#[G]E? )+)((?:[^# ]+#SE?(?: |$))+)((?:[^# ]+#[L78]E?(?: |$))*)", stacked_name)
				if firstnames_surnames:
					new_name_inflections.add(firstnames_surnames.group(1) + firstnames_surnames.group(2).strip())         # Tadeáš Hájek z Hájku -> Tadeáš Hájek
					new_name_inflections.add(firstnames_surnames.group(1) + firstnames_surnames.group(2).strip().upper()) # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK
					if len(firstnames_surnames.groups()) == 3:
						new_name_inflections.add(firstnames_surnames.group(1) + firstnames_surnames.group(2).upper() + firstnames_surnames.group(3)) # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK z Hájku
						new_name_inflections.add(firstnames_surnames.group(1) + firstnames_surnames.group(2).upper() + firstnames_surnames.group(3).upper()) # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK U HÁJKU
					#firstnames_surnames = firstnames_surnames.group(1) + firstnames_surnames.group(2).upper()
					#if firstnames_surnames != stacked_name:
						#new_name_inflections.add(firstnames_surnames)

			for n in new_name_inflections:
				subnames |= get_subnames_from_parts(regex.findall(r'(\p{L}+#GE?)', n))
				subnames |= get_subnames_from_parts(regex.findall(r'(\p{L}+#SE?(?: \p{L}+#[L78])*)', n))
			subnames = persons.get_normalized_subnames(subnames)
		for n in new_name_inflections:
			name_inflections.add(regex.sub(r'#[A-Za-z0-9]E?(?=-| |$)', '', n) if strip_nameflags else n)
	return [name_inflections, subnames]

# not used
def get_KB_names_for(_fields, preserve_flag = False):
	names = dict()
	str_name = kb_struct.get_data_for(_fields, 'NAME')
	str_aliases = kb_struct.get_data_for(_fields, 'ALIASES')
	if not preserve_flag:
		str_aliases = regex.sub(r"#(?:lang|ntype)=[^#|]*", "", str_aliases)

	names = [str_name]
	for alias in str_aliases.split(KB_MULTIVALUE_DELIM):
		alias = alias.strip()
		if alias and alias not in names:
			names.append(alias)
	return names

def get_KB_names_ntypes_for(_fields):
	names = dict()
	str_name = kb_struct.get_data_for(_fields, 'NAME')
	str_aliases = kb_struct.get_data_for(_fields, 'ALIASES')
	str_aliases = regex.sub(r"#lang=[^#|]*", "", str_aliases)

	# Assign redirects also as aliases
	aliases = str_aliases.split(KB_MULTIVALUE_DELIM) #+ kb_struct.get_data_for(_fields, 'REDIRECTS').split(KB_MULTIVALUE_DELIM)

	names[str_name] = None
	for alias in str_aliases.split(KB_MULTIVALUE_DELIM):
		ntype = regex.search(r"#ntype=([^#|]*)", alias)
		if ntype:
			ntype = ntype.group(1)
		if not ntype: # unify also for previous
			ntype = None
		k_alias = regex.sub(r"#ntype=[^#|]*", "", alias).strip()
		if k_alias and k_alias not in names:
			names[k_alias] = ntype
	return names


def process_name_inflections(line, strip_nameflags = True):
	subnames = set()
	name_inflections = set()
	line = line.strip('\n').split('\t')
	if len(line) < 5:
		raise ValueError("Some column missing: {}".format(line))
	name = line[0]
	#if name not in name_inflections:
	#	name_inflections[name] = set()
	inflections = line[3].split('|') if line[3] != '' else []
	for idx, infl in enumerate(inflections):
		inflection_parts = {}
		for i_infl_part, infl_part in enumerate(infl.split(' ')):
			inflection_parts[i_infl_part] = set()
			for infl_part_variant in infl_part.split('/'):
				inflection_parts[i_infl_part].add(regex.sub(r'(\p{L}*)(\[[^\]]+\])?', '\g<1>', infl_part_variant))
		built_name_inflections, built_subnames = build_name_variant(line[2][-1] if len(line[2]) else "", strip_nameflags, inflection_parts, idx == 0, 0, "", set())
		name_inflections |= built_name_inflections
		subnames |= built_subnames
	if len(inflections) == 0 and len(line[2]) and line[2][-1] in ['F', 'M']:
		subnames |= persons.get_normalized_subnames(src_names = [name], separate_to_names = True)
	return name, name_inflections, subnames

def process_taggednames(f_taggednames, strip_nameflags = True):
	subnames = set()
	named_inflections = {}

	path_cached_subnames = os.path.join(args.outdir, CACHED_SUBNAMES)
	path_cached_inflectednames = os.path.join(args.outdir, CACHED_INFLECTEDNAMES)
	if not args.clean_cached and os.path.isfile(path_cached_subnames) and os.path.isfile(path_cached_inflectednames):
		subnames = pickle_load(path_cached_subnames)
		named_inflections = pickle_load(path_cached_inflectednames)
	else:
		pool = Pool(args.processes)
		with open(f_taggednames) as f:
			results = pool.starmap(process_name_inflections, zip(f, itertools.repeat(strip_nameflags)))
			for name, inflections, name_subnames in results:
				if name not in named_inflections:
					named_inflections[name] = inflections
				else:
					named_inflections[name] |= inflections
				subnames |= name_subnames
		if subnames:
			pickle_dump(subnames, path_cached_subnames)
			pickle_dump(named_inflections, path_cached_inflectednames)
	namelist.addSubnames(subnames)
	return named_inflections


""" Processes a line with entity of argument determined type. """
def add_line_of_type_to_dictionary(_fields, _line_num, _type_set):
	aliases = get_KB_names_ntypes_for(_fields)
	for alias, ntype in aliases.items():
		transformed_alias = [alias]
		if  'event' in _type_set:
			if len(alias) > 1:
				transformed_alias = [alias[0].upper() + alias[1:], alias[0].lower() + alias[1:]] # capitalize destroys other uppercase letters to lowercase
		elif 'organisation' in _type_set:
			transformed_alias = [alias, ' '.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in alias.split())] # title also destroys other uppercase letters in word to lowercase

		for ta in transformed_alias:
			namelist.addVariants(ta, ntype, _line_num, _type_set, _fields)


def process_person_common(person_type, _fields, _line_num, confidence_threshold):
	""" Processes a line with entity of any subtype of person type. """

	aliases = get_KB_names_ntypes_for(_fields)
	name = kb_struct.get_data_for(_fields, 'NAME')
	confidence = float(kb_struct.get_data_for(_fields, 'CONFIDENCE'))

	processed_surnames = set()
	for n, t in aliases.items():
		length = n.count(" ") + 1
		if length >= 2 or is_capital_dominant(n):
			namelist.addVariants(n, t, _line_num, person_type, _fields)

		if confidence >= confidence_threshold:
			surname_match = SURNAME_MATCH.search(name)
			unwanted_match = UNWANTED_MATCH.search(name)
			if surname_match and not unwanted_match:
				surname = surname_match.group(0)
				if surname not in processed_surnames and surname != name:
					processed_surnames.add(surname)
					if is_capital_dominant(surname):
						namelist.addVariants(surname, t, _line_num, person_type, _fields)


def is_capital_dominant(name):
	return (name in word_freq and word_freq[name] > 0.5) or ((name[:1].lower() + name[1:]) not in word_freq)


def process_other(_fields, _line_num):
	""" Processes a line with entity of other type. """

	add_line_of_type_to_dictionary(_fields, _line_num, _fields[1])


def process_uri(_fields, _line_num):
	""" Processes all URIs for a given entry. """
	entity_head = kb_struct.get_ent_head(_fields)

	uris = []
	for uri_column_name in URI_COLUMN_NAMES:
		if uri_column_name in entity_head:
			uris.append(kb_struct.get_data_for(_fields, uri_column_name))
	if 'OTHER URL' in entity_head:
		uris.extend(kb_struct.get_data_for(_fields, 'OTHER URL').split(KB_MULTIVALUE_DELIM))
	uris = [u for u in uris if u.strip() != ""]

	for u in uris:
		namelist.entry2dict(u, _line_num)


def getLineColumns(l):
	return l.strip('\n').split("\t")


def loadListFromFile(fname):
	try:
		with open(os.path.join(args.indir, fname)) as fh:
			return fh.read().splitlines()
	except FileNotFoundError:
		print('WARNING: File "{}" was not found => continue with empty list.'.format(fname), file = sys.stderr, flush = True)
		return []


def loadWordFreq():
	try:
		fname = os.path.join(args.indir, "cs_media.wc")
		with open(fname) as frequency_file:
			dbg_f = open("freq.log", "w")
			word_freq_total = dict()
			for l in frequency_file:
				word, freq = l.rstrip().split("\t") # must be rstrip() only due to space as a key in input file
				word_freq[word] = int(freq)
				k_freq_total = word.lower()
				if k_freq_total not in word_freq_total:
					word_freq_total[k_freq_total] = 0
				word_freq_total[k_freq_total] += int(freq)
			for k in word_freq:
				word_freq[k] = word_freq[k] / word_freq_total[k.lower()]
				dbg_f.write('{}\t{}\n'.format(k, str(word_freq[k])))
			dbg_f.close()
	except FileNotFoundError:
		print('WARNING: Word frequence file "{}" was not found => ignoring word frequency.'.format(fname), file = sys.stderr, flush = True)
	gc.collect()

if __name__ == "__main__":

	if args.uri:
		# processing the KB
		for line_num, fields in enumerate(kb_struct.getKBLines(args.kb, metrics_knowledge_base.KB_PART.DATA), start = 1):
			process_uri(fields, str(line_num))

	else:
		# loading the list of titles, degrees etc. (earl, sir, king, baron, ...)
		namelist.setFreqTerms(loadListFromFile("freq_terms.lst"))

		# loading the allow list (these names will be definitely in the namelist)
		namelist.setAllowed(loadListFromFile("allow_list.lst"))

		# loading the list of first names
		#lst_firstnames = loadListFromFile("firstnames.lst")

		# loading the list of all nationalities
		#lst_nationalities = loadListFromFile("nationalities.lst")

		# load version number (string) of KB
		with open(args.kb) as kb_version_file:
			kb_version = kb_version_file.readline().strip()

		# load frequency for words
		loadWordFreq()

		namelist.setAlternatives(process_taggednames(args.taggednames, False))
		gc.collect()

		# processing the KB
		for line_num, fields in enumerate(kb_struct.getKBLines(args.kb, metrics_knowledge_base.KB_PART.DATA), start = 1):
			ent_type_set = kb_struct.get_ent_type(fields)

			if 'person' in ent_type_set:
				confidence_threshold = 20
				if 'artist' in ent_type_set or kb_struct.get_data_for(fields, 'FICTIONAL') == '1':
					confidence_threshold = 15
				process_person_common(ent_type_set, fields, str(line_num), confidence_threshold)
			else:
				process_other(fields, str(line_num))
		#gc.collect()

	# printing the output
	namelist.getTsv(include_extra = True) #not args.uri)
