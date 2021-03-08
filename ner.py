#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=4 softtabstop=4 expandtab shiftwidth=4

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
# Author: Jan Cerny, xcerny62@stud.fit.vutbr.cz
# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
# Author: David Prexta, xprext00@stud.fit.vutbr.cz
# Author: Jan Doležal, idolezal@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vutbr.cz
# Description: Reads text from the standard input or from a file, finds
#              knowledge base entities and dates, disambiguates entities,
#              resolves corefernces.

import sys

import argparse
import collections
import json
import os
import re
import requests
import tarfile
import uuid

from urllib.request import urlopen

from name_recognizer import name_recognizer as name_recognizer
from figa import marker as figa
from libs import dates
from libs.lib_loader import LibLoader
from libs.utils import remove_accent, remove_accent_unicode, get_ner_logger
from ner import configs
from ner import ner_knowledge_base as base_ner_knowledge_base
from ner.context import Context
from ner.entity import Entity
from ner.entity_register import EntityRegister
from ner.ner_loader import NerLoader


# Pro debugování:
import difflib, linecache, inspect

from libs import debug
debug.DEBUG_EN = False
from libs.debug import print_dbg_en
#

module_logger = get_ner_logger()

lng = None
word_types = None
# a list of frequent titles, degrees etc. (Mayor, King, Sir, ...)
list_titles = []
arguments = None

DISTRIBUTION_BASE = 'http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/'


def get_dicts_basepath(lng: str) -> str:
    return f'{DISTRIBUTION_BASE}/Automata/ATM_{lng}/new/'


def get_kb_basepath(lng: str) -> str:
    return f'{DISTRIBUTION_BASE}/KB/KB_{lng}/'


def check_etag_and_size(remote_path: str, etag_local_path: str, target_local_path: str) -> bool:
    need_download = True

    resp = requests.head(remote_path)
    size_remote = int(resp.headers.get('Content-Length'))
    etag_remote = resp.headers.get('ETag')

    try:
        with open(etag_local_path, 'r') as f:
            etag_local = f.read()
            if etag_local == etag_remote:
                need_download = False
        if need_download and os.path.getsize(target_local_path) == size_remote:
            need_download = False
    except FileNotFoundError as err:
        pass

    return need_download


def download_kb_or_dict_only(remote_path: str, etag_local_path: str, target_local_path: str) -> None:
    DATA_CHUNK = 4096
    downloaded_size = 0;

    print(f"  * downloading \"{os.path.basename(remote_path)}\" as \"{os.path.basename(target_local_path)}\" ...", file = sys.stderr)
    with urlopen(remote_path) as url:
        etag_remote = dict(url.getheaders())['ETag']
        size_remote_mb = int(dict(url.getheaders())['Content-Length']) / 1024.0 / 1024
        with open(target_local_path, 'wb') as fout:
            while True:
                data = url.read(DATA_CHUNK)
                if data:
                    downloaded_size += len(data) / 1024.0 / 1024
                    print(f"    * downloaded: {downloaded_size:.2f} / {size_remote_mb:.2f} MB...", file = sys.stderr, end = '\r')
                    fout.write(data)
                else:
                    print(f"    * download completed ...                          ", file = sys.stderr)
                    with open(etag_local_path, 'w') as fetag:
                        fetag.write(etag_remote)
                    break


def download_with_check(remote_path: str, etag_local_path: str, target_local_path: str) -> None:
    print(f"  * checking \"{os.path.basename(target_local_path)}\" ...", file = sys.stderr)
    need_download = check_etag_and_size(remote_path, etag_local_path, target_local_path)

    if need_download:
        download_kb_or_dict_only(remote_path, etag_local_path, target_local_path)
    else:
        print(f"  * already downloaded file \"{os.path.basename(target_local_path)}\" - using local one ...", file = sys.stderr)


def get_dicts_remote_version(lng: str) -> dict:
    resp = requests.get(f'{get_dicts_basepath(lng)}/VERSIONS.json')
    if resp.status_code != 200:
        raise Exception('Error occurs while downloading VERSION file of dictionaries.')
    return resp.json()


def offsets_of_paragraphs(input_string):
    """
    Returns a list of starting offsets of each paragraph in input_string.
    Example:
      * Martin Havelka je ........ M. Havelka bol ....... .
      * Maros Havelka .................
      * ..... M. Havelka ......
    """

    assert isinstance(input_string, str)

    result = [0]
    result.extend((par_match.end() for par_match in re.finditer(r"(\r?\n|\r)\1+", input_string))) # {?2×LF|?2×CRLF|?2×CR} ? nový odstavec
    return result



def find_proper_nouns(input_string):
    """ Returns a list of proper nouns. """
    assert isinstance(input_string, str)
    
    result = []
    re_proper_noun_preps = "";
    for prep in word_types.PROPER_NOUNS_PREPS:
        re_proper_noun_preps += r'| {}'.format(re.escape(prep))
    proper_noun_regex = re.compile(r"(?<!\. |\? |! |: |\s{2})[A-Z][A-Za-z\'\-]*( [A-Z][A-Za-z\'\-]*" + re_proper_noun_preps + r")* [A-Z][A-Za-z\'\-]*") # !!!
    for pn in re.finditer(proper_noun_regex, input_string):
        fields = pn.group(0).split()
        if fields[0] not in list_titles and pn.start() != 0:
            result.append((pn.start(), pn.end()))
    return result


def fix_poor_disambiguation(entities, context):
    """ Fixes the entity sense if poorly_disambiguated is set to True. """
    assert isinstance(entities, list) # list of Entity
    assert isinstance(context, Context)

    strong_entities = {}
    strong_entities_by_id = {}
    entities = [e for e in entities if isinstance(e, Entity) and not e.is_coreference]

    for e in entities:
        if not e.poorly_disambiguated:
            if e.source not in strong_entities:
                strong_entities[e.source] = []
            strong_entities[e.source].append(e.get_preferred_entity())

            if e.get_preferred_sense() not in strong_entities_by_id:
                strong_entities_by_id[e.get_preferred_sense()] = []
            strong_entities_by_id[e.get_preferred_sense()].append(e.get_preferred_entity())

    for e in entities:
        if e.poorly_disambiguated:
            candidates = []
            for s in e.senses:
                if s in strong_entities_by_id:
                    candidates += strong_entities_by_id[s]

            if candidates != []:
                e.set_preferred_sense(get_nearest_entity(e, candidates))
                e.poorly_disambiguated = False
            elif e.source in strong_entities:
                e.set_preferred_sense(get_nearest_entity(e, strong_entities[e.source]))
                e.poorly_disambiguated = False


def add_unknown_names(kb, entities_and_dates, input_string, register):
    """ Finding unknown names. """
    assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
    assert isinstance(entities_and_dates, list) # list of Entity and dates.Date
    assert isinstance(input_string, str)
    assert isinstance(register, EntityRegister)

    global output

    nr = name_recognizer.NameRecognizer()
    try:
        data_rows = nr.recognize_names(input_string, figa_out=output)
    except Exception:
        return

    name_entities = []

    for dr in data_rows:
        name_entities.append(Entity.from_data_row(kb, dr, input_string, register))

    new_name_entities = []

    for i in range(len(name_entities)):
        assigned = None
        for j in range(0, i):
            if name_entities[i].source == name_entities[j].source:
                assigned = name_entities[j].senses
                break

        if assigned:
            name_entities[i].senses = assigned.copy()
        else:
            name_entities[i].senses = set([-(i+1)])

    # resolving overlapping names
    for ne in name_entities:
        substring   = False
        overlapping = False
        overlaps    = []
        for ed in entities_and_dates:
            if not isinstance(ed, Entity):
                continue

            if ne.is_equal(ed) or  ed.is_overlapping(ne):
                substring = True
                break
            elif ne.is_overlapping(ed):
                overlapping = True
                overlaps.append(ed)
        if not (substring or overlapping):
            new_name_entities.append(ne)
        elif overlapping:
            senses = set()
            for o in overlaps:
                senses = senses | o.senses
                entities_and_dates.remove(o)
            ne.senses = senses.copy()
            new_name_entities.append(ne)

    # inserting names into entity list
    for nne in new_name_entities:
        for i in range(len(entities_and_dates)):
            if i == len(entities_and_dates)-1:
                entities_and_dates.append(nne)
                break
            elif nne.start_offset >= entities_and_dates[i].start_offset and \
            nne.start_offset < entities_and_dates[i+1].start_offset:
                entities_and_dates.insert(i+1, nne)
                break
            elif nne.start_offset < entities_and_dates[0].start_offset:
                entities_and_dates.insert(0, nne)
                break

    adjust_coreferences(entities_and_dates, new_name_entities)

def adjust_coreferences(entities_and_dates, new_name_entities):
    ed            = entities_and_dates
    names         = new_name_entities
    wanted_corefs = word_types.PRONOUNS.keys()

    ed_size       = len(ed)

    if not ed:
        return

    for n in names:
        i_prev = None
        i_next = None
        index  = None

        for i in range(ed_size):
            if ed[i] == n:
                index = i
                break

        for i in range(index+1, ed_size):
            if isinstance(ed[i], Entity) and ed[i].is_person():
                i_next = i
                break

        for i in range(index-1, -1, -1):
            if isinstance(ed[i], Entity) and ed[i].is_person():
                i_prev = i
                break

        # Nothing to do here
        if i_next == None: break
        if ed[i_next].is_name: continue

        for i in range(index+1, i_next or ed_size):
            if isinstance(ed[i], Entity) and ed[i].is_coreference and \
            ed[i].source.lower() in wanted_corefs:
                if len(n.senses) == 0:
                    continue
                sense   = ed[i].get_preferred_sense()
                n_sense = list(n.senses)[0]
                if not i_prev:
                    ed[i].set_preferred_sense(n_sense)
                elif len(ed[i_prev].senses) > 0 and \
                sense == list(ed[i_prev].senses)[0] and sense != n_sense:
                        ed[i].set_preferred_sense(n_sense)

def resolve_coreferences(entities, context, print_all, register):
    """ Resolves coreferences. """
    assert isinstance(entities, list) # list of Entity
    assert isinstance(context, Context)
    assert isinstance(print_all, bool)
    assert isinstance(register, EntityRegister)

    for e in entities:
        # adding propriate candidates into people set
        if not e.is_coreference and e.has_preferred_sense():
            ent_type_set = e.kb.get_ent_type(e.get_preferred_sense())
            if 'person' in ent_type_set:
                context.people_in_text.add(e.get_preferred_sense())

    for e in entities:
        if e.is_coreference:
            # coreferences by a name to people out of context are discarded
            if not print_all:
                e.partial_match_senses = set([s for s in e.partial_match_senses if s in context.people_in_text])
                if e.partial_match_senses:
                    # choosing the candidate with the highest confidence score
                    sense = sorted(list(e.partial_match_senses), key=lambda candidate: context.kb.get_score(candidate), reverse=True)[0]
                    candidates = list(register.id2entity[sense])
                    if not e.source.lower().startswith("the "):
                        # each candidate has to contain the text of a given entity
                        candidates = (c for c in candidates if remove_accent_unicode(e.source).lower() in remove_accent_unicode(c.source).lower())
                    # choosing the nearest predecessor candidate for a coreference
                    entity = get_nearest_predecessor(e, candidates)
                    if entity:
                        e.set_preferred_sense(entity)
                elif e.source.lower() in word_types.PRONOUNS:
                    e.resolve_pronoun_coreference(context)
                elif e.senses:
                    e.is_coreference = False
                    e.disambiguate_without_context()
                    e.disambiguate_with_context(context)
        if e.has_preferred_sense():
            context.update(e)


def get_nearest_predecessor(_entity, _candidates):
    """ Returns the nearest predecessor for a given entity from a given list of candidates. """
    assert isinstance(_entity, Entity)
    assert isinstance(_candidates, collections.Iterable) # iterable of Entity

    # sorting candidates according to the distance from a given entity # NOTE: Nešlo by to napsat lépe?
    candidates = sorted(_candidates, key=lambda candidate: _entity.start_offset - candidate.start_offset)
    for candidate in candidates:
        if _entity.start_offset - candidate.start_offset > 0:
            return candidate


def get_nearest_entity(_entity, _candidates):
    """ Returns the nearest entity for a given entity from a given list of candidates. """
    assert isinstance(_entity, Entity)
    assert isinstance(_candidates, collections.Iterable) # iterable of Entity

    # sorting candidates according to the distance from a given entity
    candidates = sorted(_candidates, key=lambda candidate: abs(_entity.start_offset - candidate.start_offset))

    return candidates[0].preferred_sense


FigaOutput = collections.namedtuple("FigaOutput", "kb_rows start_offset end_offset fragment flag")


def parseFigaOutput(figa_output):
    """
    Parsuje výstup z figy.

    Syntax výstupního formátu v Backusově-Naurově formě (BNF):
        <výstup Figa> :== <řádek výstupu>
            | <řádek výstupu> <výstup Figa>
        <řádek výstupu> :== <čísla řádků do KB> "\t" <počáteční offset>
                "\t" <koncový offset> "\t" <fragment> "\t" <příznak> "\n"
        <čísla řádků do KB> :== <číslo>
            | <číslo> ";" <čísla řádků do KB>
    kde:
        <čísla řádků do KB> odkazují na řádky ve znalostní bázi s entitami, jenž mají mezi atributy <fragment> (řádek 0 značí zájmeno – coreference)
        <počáteční offset> a <koncový offset> jsou pozice prvního a posledního znaku řetězce <fragment> (na pozici 1 leží první znak vstupního textu) – to je třeba upravit, aby šlo využít přímo input[start_offset:end_offset]
        <příznak> může nabývat dvou hodnot: F – fragment plně odpovídá atributu odkazovaných entit; S – byl tolerován překlep ve fragmentu
    """

    # Formát "číslo_řádku[;číslo_řádku]\tpočáteční_offset\tkoncový_offset\tnázev_entity\tF"
    for line in figa_output.split("\n"):
        if line != "":
            kb_rows, start_offset, end_offset, name, flag = line.split("\t")
            yield FigaOutput(map(int, kb_rows.split(";")), int(start_offset)-1, int(end_offset), name, flag) # Figa má start_offset+1 (end_offset má dobře).

seek_names = None
output = None


def get_dict_path(lowercase: bool) -> str:
    lower = ""
    if lowercase:
        lower = "-lower"

    path_to_figa_dict = os.path.abspath(os.path.join(arguments.indir, f"automata{lower}"))
    if os.path.isfile(path_to_figa_dict + ".dct"):
        path_to_figa_dict += ".dct" # DARTS
    else:
        path_to_figa_dict += ".ct" # CEDAR

    return path_to_figa_dict


def get_entities_from_figa(kb, input_string, lowercase, global_senses, register, print_score):
    """ Returns the list of Entity objects from figa. """ # TODO: Možná by nebylo od věci toto zapouzdřit do třídy jako v "get_entities.py".
    assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
    assert isinstance(input_string, str)
    assert isinstance(lowercase, bool)
    assert isinstance(global_senses, set)
    assert isinstance(register, EntityRegister)
    assert isinstance(print_score, bool)

    global seek_names
    global output
    
    input_string

    if not seek_names:
        seek_names = figa.marker()
        path_to_figa_dict = get_dict_path(lowercase)
        if not seek_names.load_dict(path_to_figa_dict):
            raise RuntimeError('Could not load dictionary (file "{}" does not exist or permission denied).'.format(path_to_figa_dict))

    # getting data from figa
    if lowercase:
        output = seek_names.lookup_string(input_string.lower())
    else:
        output = seek_names.lookup_string(input_string)
    entities = []

    # processing figa output and creating Entity objects
    for line in parseFigaOutput(output):
        global lng
        e = NerLoader.load(module = "entity", lang = lng, initiate = "Entity")
        e.create(line, kb, input_string, register)
        global_senses.update(e.senses)
        e.display_score = print_score
        entities.append(e)

    return entities

def remove_shorter_entities(entities):
    """ Removing shorter entity from overlapping entities. """
    assert isinstance(entities, list) # list of Entity

    # figa should always return the longest match first
    entity_offsets = set()
    new_entities = []
    for e in entities:
        current_offset = set(range(e.start_offset, e.end_offset + 1))
        if current_offset & entity_offsets == set():
            entity_offsets.update(current_offset)
            new_entities.append(e)
    return new_entities


def resolve_overlapping_proper_nouns(entities, input_string):
    """ Resolving overlapping entities and proper nouns. """
    assert isinstance(entities, list) # list of Entity
    assert isinstance(input_string, str)
    
    # input with removed accent
    input_without_accent = remove_accent_unicode(input_string)

    # finding proper nouns
    proper_nouns = find_proper_nouns(input_without_accent)
    proper_nouns_offsets = set()
    entities_offsets = set()
    # index gives for each offset a particular proper noun
    proper_nouns_index = {}
    for pn in proper_nouns:
        # computing proper nouns offsets # NOTE: Nešlo by to napsat lépe?
        proper_noun_offsets = range(pn[0], pn[1])
        proper_nouns_offsets.update(proper_noun_offsets)
        for pno in proper_noun_offsets:
            proper_nouns_index[pno] = pn
    new_entities = []
    # computing entities offsets
    for e in entities:
        entity_offsets = range(e.start_offset, e.end_offset)
        entities_offsets.update(entity_offsets)
    # searching for solitary spaces (e.g. Canadian Paul Verlaine)
    diff_pn_e = proper_nouns_offsets - entities_offsets
    spaces_in_diff_pn_e = set([o for o in diff_pn_e if input_without_accent[o] == ' '])
    solitary_spaces = set([o for o in spaces_in_diff_pn_e if (o - 1 not in spaces_in_diff_pn_e) and (o + 1 not in spaces_in_diff_pn_e)])
    # going through entities and checking whether they overlap with proper nouns
    for e in entities:
        entity_offsets = set(range(e.start_offset, e.end_offset))
        overlap = proper_nouns_offsets & entity_offsets
        # if there is an overlap
        if overlap:
            # there could be more than one overlapping proper noun
            overlapping_proper_nouns = set([proper_nouns_index[o] for o in overlap])
            for opn in overlapping_proper_nouns:
                opn_offsets = set(range(opn[0], opn[1]))
                diff_opn_e = opn_offsets - entities_offsets
                # how many spaces and apostrophes are there in the difference string
                spaces = [o for o in diff_opn_e if (input_without_accent[o] == ' ') and (o not in solitary_spaces)]
                apostrophes = [o for o in diff_opn_e if input_without_accent[o] == "'"]
                if not spaces or apostrophes:
                    new_entities.append(e)
                    break
        else:
            new_entities.append(e)
    return new_entities

def remove_nearby_entities(kb, entities, input_string):
    """ Filtering out entities that are next to another entity (excluding dates). """
    assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
    assert isinstance(entities, list) # list of Entity
    assert isinstance(input_string, str)
    
    # determining whether two entities lie next to each other
    ent_ind = 0
    for ent_ind in range(1, len(entities)):
        ent = entities[ent_ind]
        ent_bef = entities[ent_ind - 1]
        if ent.has_preferred_sense() and ent.source.lower() not in word_types.PRONOUNS:
            if ent_bef.has_preferred_sense() and ent_bef.source.lower() not in word_types.PRONOUNS:
                # if both entities are divided only by space and they are of the same type
                if re.search("^[ ]+$", input_string[ent_bef.end_offset:ent.start_offset]):
                    ent_type_set = set([kb.get_ent_type(ent.get_preferred_sense())])
                    ent_bef_type_set = set([kb.get_ent_type(ent_bef.get_preferred_sense())])
                    mutual_type_set = ent_type_set & ent_bef_type_set
                    if {"person", "location"} & mutual_type_set:
                        ent.next_to_same_type = True
                        ent_bef.next_to_same_type = True

    # filtering out entities that are next to another entity (excluding dates)
    new_entities = [e for e in entities if not e.next_to_same_type]
    return new_entities


def recognize(kb, input_string, print_all=False, print_result=True, print_score=False, lowercase=False, remove=False, split_interval=True, find_names=False):
    """
    Prints a list of entities found in input_string.

    kb - a knowledge base
    print_all - if false, all entities are disambiguated
    print_result - if True, the result is both returned as a list of entities and printed to stdout; otherwise, it is only returned
    print_score - similar to print_all, but also prints the score for each entity alternative
    lowercase - the input string is lowercased
    remove - removes accent from the input string
    split_interval - split dates intervals in function dates.find_dates()
    """
    assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
    assert isinstance(input_string, str)
    assert isinstance(print_all, bool)
    assert isinstance(print_result, bool)
    assert isinstance(print_score, bool)
    assert isinstance(lowercase, bool)
    assert isinstance(remove, bool)
    assert isinstance(split_interval, bool)
    assert isinstance(find_names, bool)

    def debugChangesInEntities(entities, responsible_line):
        if debug.DEBUG_EN:
            global debug_last_status_of_entities
            if "debug_last_status_of_entities" in globals():
                new_status_of_entities = [e+"\n" for e in map(str, sorted(entities, key=lambda ent: ent.start_offset))]
                diff = "".join(difflib.unified_diff(debug_last_status_of_entities, new_status_of_entities, fromfile='before', tofile='after', n=0))[:-1]
                if diff:
                    print_dbg_en(responsible_line, diff, delim="\n", stack_num=2)
                debug_last_status_of_entities = new_status_of_entities
            else:
                debug_last_status_of_entities = [e+"\n" for e in map(str, sorted(entities, key=lambda ent: ent.start_offset))]

    # replacing non-printable characters and semicolon with space characters
    input_string = re.sub("[;\x01-\x08\x0e-\x1f\x0c\x7f]", " ", input_string)

    # running with parametr --remove_accent
    if remove:
        input_string = remove_accent(input_string)

    # creating entity register
    register = EntityRegister()
    # a set of all possible senses
    global_senses = set()

    # getting entities from figa
    figa_entities = get_entities_from_figa(kb, input_string, lowercase, global_senses, register, print_score)
    debugChangesInEntities(figa_entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    # retaining only possible coreferences for each entity
    for e in figa_entities:
        e.partial_match_senses = e.partial_match_senses & global_senses

    # removing shorter entity from overlapping entities
    figa_entities = remove_shorter_entities(figa_entities)
    debugChangesInEntities(figa_entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    # removing entities without any sense
    nationalities = []
    entities = []
    for e in figa_entities:
        if e.is_nationality:
            nationalities.append(e)
        elif e.senses or e.partial_match_senses or e.source.lower() in word_types.PRONOUNS:
            entities.append(e)
    debugChangesInEntities(entities, "removing entities without any sense")

    # searches for dates and intervals in the input
    dates_and_intervals = dates.find_dates(input_string, split_interval=split_interval)

    # resolving overlapping dates and entities
    entity_offsets = set()
    for e in entities:
        entity_offsets.update(set(range(e.start_offset, e.end_offset + 1)))
    dates_and_intervals = [d for d in dates_and_intervals if set(range(d.start_offset, d.end_offset + 1)) & entity_offsets == set()]

    # merges entities with dates
    entities_and_dates = []
    entities_and_dates.extend(dates_and_intervals)
    entities_and_dates.extend(entities)

    # sorts entities and dates according to their start offsets
    entities_and_dates.sort(key=lambda ent : ent.start_offset)

    # NOTE: Odtut se dějí zajímavé věci {
    # disambiguates without context
    [e.disambiguate_without_context() for e in entities] # NOTE: Teoreticky se po této disabiguaci mohou v entities vyzkytovat entity bez významu.
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    paragraphs = offsets_of_paragraphs(input_string)
    context = Context(entities_and_dates, kb, paragraphs, nationalities)

    # disambiguates with context
    [e.disambiguate_with_context(context) for e in entities]
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))
    fix_poor_disambiguation(entities, context)
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))
    context = Context(entities_and_dates, kb, paragraphs, nationalities) # Znovu se vytváří kontext, aby došlo k novému vypočítání statistik pro každý odstavec. Disabiguací s kontextem totiž došlo ke změnám preferovaných významů některých entit.

    # resolving coreferences
    name_coreferences = [e for e in entities if e.source.lower() not in word_types.PRONOUNS and not e.source.lower().startswith("the ")]
    resolve_coreferences(name_coreferences, context, print_all, register) # Zde se ověřuje, zda-li části jmen jsou odkazy nebo samostatné entity.
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))
    resolve_coreferences(entities, context, print_all, register) # Dle předchozích kroků se dosadí správné odkazy.
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    # resolving overlapping entities and proper nouns
    entities = resolve_overlapping_proper_nouns(entities, input_string)
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    # determining whether two entities lie next to each other
    entities = set(remove_nearby_entities(kb, entities, input_string))
    debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

    # updating entities_and_dates
    entities_and_dates = [e for e in entities_and_dates if isinstance(e, dates.Date) or e in entities]
    debugChangesInEntities(entities_and_dates, "updating entities_and_dates")

    # finding unknown names
    if find_names:
        add_unknown_names(kb, entities_and_dates, input_string, register)

    # omitting entities without a sense
    if entities_and_dates:
        if not (print_all or print_score):
            entities_and_dates = [e for e in entities_and_dates if isinstance(e, dates.Date) or e.has_preferred_sense() or e.is_name]
        else:
            if print_all:
                for e in entities_and_dates:
                    if isinstance(e, Entity):
                        e.set_preferred_sense(None)
            entities_and_dates = [e for e in entities_and_dates if isinstance(e, dates.Date) or (e.is_coreference and e.partial_match_senses) or (not e.is_coreference and e.senses) or e.is_name]
    debugChangesInEntities(entities_and_dates, "omitting entities without a sense")

    if print_result:
        print("\n".join(map(str, entities_and_dates)))

    return entities_and_dates


def main():
    global arguments
    global lng
    global list_titles
    global word_types
    
    # argument parsing
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--all', action='store_true', default=False, dest='all', help='Prints all entities without disambiguation.')
    group.add_argument('-s', '--score', action='store_true', default=False, dest='score', help='Prints all possible senses with respective score values.')
    parser.add_argument('-q', '--lang', default = 'cs', help='Language of recognition / disambiguation (default: %(default)s).')
    parser.add_argument('-d', '--daemon-mode', action='store_true', default=False, help='Runs ner.py in daemon mode.')
    parser.add_argument('-f', '--file',  help='Uses a given file as as an input.')
    parser.add_argument('-r', '--remove-accent', action='store_true', default=False, help="Removes accent in input.")
    parser.add_argument('-l', '--lowercase', action='store_true', default=False, help="Changes all characters in input to the lowercase characters.")
    parser.add_argument('-n', '--names', action='store_true', default=False, help="Recognizes and prints all names with start and end offsets.")
#    parser.add_argument('-I', '--indir', type = str, default=os.path.join(os.getcwd(), 'ner/inputs'), help="Input directory, where automata/dictionaries and other input files are stored (default: %(default)s).")
    parser.add_argument('--update', action="store_true", help="Check for new version of input files and update to a new one, if any.")
    parser.add_argument("--own_kb_daemon", action="store_true", dest="own_kb_daemon", help=("Run own KB daemon although another already running."))
    parser.add_argument("--debug", action="store_true", help="Enable debugging reports.")

    arguments = parser.parse_args()

    arguments.lang = arguments.lang.lower()
    if arguments.lang in configs.LANGS_MAP:
        arguments.lang = configs.LANGS_MAP[arguments.lang]

    if arguments.lang in configs.LANGS_ALLOWED:
        lng = arguments.lang
    else:
        if len(configs.LANGS_ALLOWED) == 1:
            lng = next(iter(configs.LANGS_ALLOWED))
        else:
            raise Exception(f'Please select one of supported language ({", ".join(configs.LANGS_ALLOWED)}) by parameter "--lang".')

    if not debug.DEBUG_EN and arguments.debug:
        debug.DEBUG_EN = True

    need_update = False
    arguments.indir = os.path.join(os.getcwd(), 'ner/inputs')

    fpath_version = os.path.join(arguments.indir, "VERSIONS.json")

    if not os.path.isdir(arguments.indir):
        os.makedirs(arguments.indir)
        need_update = True
    else:
        if not os.path.isfile(fpath_version):
            need_update = True
        else:
            dict_path = get_dict_path(arguments.lowercase)
            if not os.path.isfile(dict_path):
                need_update = True

    version_remote = {}
    version_local = {}
    if not need_update and arguments.update:
        with open(fpath_version, 'r') as f:
            version_local = json.load(f)
        version_remote = get_dicts_remote_version(lng)
        if version_remote.get('KB') > version_local.get('KB') or version_remote.get('DICTS') != version_remote.get('DICTS') or version_remote.get('CZECH NAMEGEN') != version_local.get('CZECH NAMEGEN'):
            need_update = True

    if need_update:
        if not version_remote:
            version_remote = get_dicts_remote_version(lng)
        KB_version = version_remote.get('KB')

        print(f"Updating dicts from version \"{version_local.get('KB') if version_local.get('KB') else 'UNKNOWN'}\" to version \"{version_remote.get('KB')}\"...", file = sys.stderr)

        tgz_fname = f'ATM_{KB_version}.tar.gz'
        tgz_local_path = os.path.join(arguments.indir, tgz_fname)
        tgz_etag_path = os.path.join(arguments.indir, f'.{tgz_fname}.etag')
        tgz_remote_path = f'{get_dicts_basepath(lng)}/ATM_{KB_version}.tar.gz'

        download_with_check(tgz_remote_path, tgz_etag_path, tgz_local_path)

        print(f"  * extracting \"{tgz_fname}\" ...", file = sys.stderr)
        tgz = tarfile.open(tgz_local_path, 'r:gz')
        tgz.extractall(arguments.indir)
        tgz.close()

    # KB check and download - check if exists appropriate version of KB, over which dicts were created; othervise download it
    print(f"Checking KB for the relevant required version \"{version_remote.get('KB')}\"...", file = sys.stderr)
    with open(fpath_version, 'r') as f:
        version_local = json.load(f)
        KB_version = version_local.get('KB')
        kb_fname = f'KB.tsv'
        kb_local_path = os.path.join(arguments.indir, kb_fname)
        kb_etag_path = os.path.join(arguments.indir, f'.{kb_fname}.etag')
        kb_remote_path = f'{get_kb_basepath(lng)}/KB_{KB_version}/KB.tsv'

        download_with_check(kb_remote_path, kb_etag_path, kb_local_path)

    # a list of frequent titles, degrees etc. (Mayor, King, Sir, ...)
    f_titles = os.path.abspath(os.path.join(arguments.indir, "freq_terms_filtred.all"))
    list_titles = [line.strip() for line in open(f_titles)] if os.path.exists(f_titles) else []

    word_types = LibLoader.load('word_types', lng, 'WordTypes')

    # allowed tokens for daemon mode
    tokens = set(["NER_NEW_FILE", "NER_END", "NER_NEW_FILE_ALL", "NER_END_ALL", "NER_NEW_FILE_SCORE", "NER_END_SCORE", "NER_NEW_FILE_NAMES", "NER_END_NAMES"])

    # loading knowledge base
    kb = NerLoader.load(module = "ner_knowledge_base", lang = lng, initiate = "KnowledgeBase")
    if arguments.own_kb_daemon:
        kb_daemon_run = True
        while kb_daemon_run:
            kb_shm_name = "/decipherKB-%s-daemon_shm-%s" % (lng, uuid.uuid4())
            kb.init(kb_shm_name=kb_shm_name)
            kb_daemon_run = kb.check()
    else:
        kb_shm_name = "/decipherKB-%s-daemon_shm-999" % lng
        kb.init(kb_shm_name=kb_shm_name)

    try:
        kb.start()
        kb.initName_dict()

        if arguments.daemon_mode:
            input_string = ""
            while True:
                line = sys.stdin.readline().rstrip()
                if line in tokens:
                    if "ALL" in line:
                        recognize(kb, input_string, print_all=True, lowercase=arguments.lowercase, remove=arguments.remove_accent)
                    elif "SCORE" in line:
                        recognize(kb, input_string, print_score=True, lowercase=arguments.lowercase, remove=arguments.remove_accent)
                    elif "NAMES" in line:
                        recognize(kb, input_string, find_names=True, lowercase=arguments.lowercase, remove=arguments.remove_accent)
                    else:
                        recognize(kb, input_string, print_all=False, lowercase=arguments.lowercase, remove=arguments.remove_accent)
                    print(line)
                    sys.stdout.flush()
                    input_string = ""
                    if "END" in line:
                        break
                else:
                    input_string += line + "\n"
        else:
            # reading input data from file
            if arguments.file:
                with open(arguments.file) as f:
                    input_string = f.read()
            # reading input data from stdin
            else:
                input_string = sys.stdin.read()
            input_string = input_string.strip()
            recognize(kb, input_string, print_all=arguments.all, print_score=arguments.score, lowercase=arguments.lowercase, remove=arguments.remove_accent, find_names=arguments.names)
    finally:
        kb.end()

if __name__ == "__main__":
    main()
