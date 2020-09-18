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
import os
import re
import uuid
import copy
import string

# Pro debugování:
import difflib, linecache, inspect

# <LOKÁLNÍ IMPORTY>
from .name_recognizer import name_recognizer as name_recognizer
from .figa import marker as figa
from .libs.utils import remove_accent, remove_accent_unicode, get_ner_logger
from .ner_lib.configs import INPUTS_DIR, LANGS_ALLOWED
from .ner_lib import ner_knowledge_base as base_ner_knowledge_base
from .ner_lib import dates as base_dates
from .ner_lib.ner_loader import NerLoader
from .ner_lib.context import Context
from .ner_lib.entity import Entity
from .ner_lib.entity_register import EntityRegister

# Pro debugování:
from .ner_lib import debug
debug.DEBUG_EN = False
from .ner_lib.debug import print_dbg_en, print_dbg
# </LOKÁLNÍ IMPORTY>

module_logger = get_ner_logger()

class Ner():
    def __init__(self, language, own_kb_daemon=False):
        self._running = False
        self.language = language
        self.ner_vars = NerLoader.load(module = "ner_vars", lang = self.language, initiate = "NerVars")
        self.dates = base_dates.importLanguageModule(self.language)
        self.figa_seek_names = None
        self.kb = None
        
        # a list of frequent titles, degrees etc. (Mayor, King, Sir, ...)
        self.F_TITLES = os.path.abspath(os.path.join(INPUTS_DIR, self.language, "freq_terms_filtred.all"))
        self.LIST_OF_TITLES = [line.strip() for line in open(self.F_TITLES)] if os.path.exists(self.F_TITLES) else []
        
        # init knowledge base
        self._init_knowledge_base(own_kb_daemon)
    
    def __del__(self):
        self.end()
    
    def start(self):
        if self._running:
            return
        
        # loading knowledge base
        self.kb.start()
        self.kb.initName_dict()
        
        self._running = True
    
    def end(self):
        if not self._running:
            return
        
        if self.kb:
            self.kb.end()
        
        self._running = False
    
    def setPathKb(self, path_kb):
        assert not self._running
        self.kb.path_kb = path_kb
    
    def getPathKb(self):
        return self.kb.path_kb
    
    def _init_knowledge_base(self, own_kb_daemon):
        self.kb = NerLoader.load(module = "ner_knowledge_base", lang = self.language, initiate = "KnowledgeBase")
        if own_kb_daemon:
            kb_daemon_run = True
            while kb_daemon_run:
                kb_shm_name = "/decipherKB-daemon_shm-%s-%s" % (self.language, uuid.uuid4())
                self.kb.init(kb_shm_name=kb_shm_name)
                kb_daemon_run = self.kb.check()
        else:
            self.kb.init()
    
    def find_proper_nouns(self, input_string):
        """ Returns a list of proper nouns. """
        assert isinstance(input_string, str)
        
        result = []
        re_proper_noun_preps = "";
        for prep in self.ner_vars.PROPER_NOUNS_PREPS:
            re_proper_noun_preps += r'| {}'.format(re.escape(prep))
        proper_noun_regex = re.compile(r"(?<!\. |\? |! |: |\s{2})[A-Z][A-Za-z\'\-]*( [A-Z][A-Za-z\'\-]*" + re_proper_noun_preps + r")* [A-Z][A-Za-z\'\-]*") # !!!
        for pn in re.finditer(proper_noun_regex, input_string):
            fields = pn.group(0).split()
            if fields[0] not in self.LIST_OF_TITLES and pn.start() != 0:
                result.append((pn.start(), pn.end()))
        return result

    def add_unknown_names(self, kb, entities_and_dates, input_string, register, figa_raw_output=None):
        """ Finding unknown names. """
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(entities_and_dates, list) # list of Entity and dates.Date
        assert isinstance(input_string, str)
        assert isinstance(register, EntityRegister)

        nr = name_recognizer.NameRecognizer()
        try:
            data_rows = nr.recognize_names(input_string, figa_out=figa_raw_output)
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

        self.adjust_coreferences(entities_and_dates, new_name_entities)

    def adjust_coreferences(self, entities_and_dates, new_name_entities):
        ed            = entities_and_dates
        names         = new_name_entities
        wanted_corefs = self.ner_vars.PRONOUNS.keys()

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

    def resolve_coreferences(self, entities, context, print_all, register):
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
                    elif e.source.lower() in self.ner_vars.PRONOUNS:
                        e.resolve_pronoun_coreference(context)
                    elif e.senses:
                        e.is_coreference = False
                        e.disambiguate_without_context()
                        e.disambiguate_with_context(context)
            if e.has_preferred_sense():
                context.update(e)

    def get_entities_from_figa(self, kb, input_string, lowercase, global_senses, register, print_score, print_uri, entities_overlap=False):
        """ Returns the list of Entity objects from figa. """ # TODO: Možná by nebylo od věci toto zapouzdřit do třídy jako v "get_entities.py".
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(input_string, str)
        assert isinstance(lowercase, bool)
        assert isinstance(global_senses, set)
        assert isinstance(register, EntityRegister)
        assert isinstance(print_score, bool)
        assert isinstance(print_uri, bool)

        figa_seek_names_config = {"overlap": entities_overlap, "lowercase": lowercase, "language": self.language}

        if not self.figa_seek_names or self.figa_seek_names_config != figa_seek_names_config:
            self.figa_seek_names_config = figa_seek_names_config
            cfg = self.figa_seek_names_config
            self.figa_seek_names = figa.marker(over=cfg["overlap"])

            lower = ""
            if cfg["lowercase"]:
                lower = "-lower"

            path_to_figa_dict = os.path.dirname(os.path.realpath(__file__)) + f"/ner_lib/inputs/{cfg['language']}/automata{lower}"
            if os.path.isfile(path_to_figa_dict + ".dct"):
                path_to_figa_dict += ".dct" # DARTS
            else:
                path_to_figa_dict += ".ct" # CEDAR
            if not self.figa_seek_names.load_dict(path_to_figa_dict):
                raise RuntimeError('Could not load dictionary (file "{}" does not exist or permission denied).'.format(path_to_figa_dict))

        # getting data from figa
        if lowercase:
            raw_output = self.figa_seek_names.lookup_string(input_string.lower())
        else:
            raw_output = self.figa_seek_names.lookup_string(input_string)
        entities = []

        # processing figa output and creating Entity objects
        for line in parseFigaOutput(raw_output):
            e = NerLoader.load(module = "entity", lang = self.language, initiate = "Entity")
            e.create(line, kb, input_string, register)
            global_senses.update(e.senses)
            e.display_score = print_score
            e.display_uri = print_uri
            entities.append(e)

        return entities, raw_output

    def resolve_overlapping_proper_nouns(self, entities, input_string):
        """ Resolving overlapping entities and proper nouns. """
        assert isinstance(entities, list) # list of Entity
        assert isinstance(input_string, str)
        
        # input with removed accent
        input_without_accent = remove_accent_unicode(input_string)

        # finding proper nouns
        proper_nouns = self.find_proper_nouns(input_without_accent)
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

    def remove_nearby_entities(self, kb, entities, input_string):
        """ Filtering out entities that are next to another entity (excluding dates). """
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(entities, list) # list of Entity
        assert isinstance(input_string, str)
        
        # determining whether two entities lie next to each other
        ent_ind = 0
        for ent_ind in range(1, len(entities)):
            ent = entities[ent_ind]
            ent_bef = entities[ent_ind - 1]
            if ent.has_preferred_sense() and ent.source.lower() not in self.ner_vars.PRONOUNS:
                if ent_bef.has_preferred_sense() and ent_bef.source.lower() not in self.ner_vars.PRONOUNS:
                    # if both entities are divided only by space and they are of the same type
                    if re.search("^[ ]+$", input_string[ent_bef.end_offset:ent.start_offset]):
                        ent_type_set = kb.get_ent_type(ent.get_preferred_sense())
                        ent_bef_type_set = kb.get_ent_type(ent_bef.get_preferred_sense())
                        mutual_type_set = ent_type_set & ent_bef_type_set
                        if {"person", "location"} & mutual_type_set:
                            ent.next_to_same_type = True
                            ent_bef.next_to_same_type = True

        # filtering out entities that are next to another entity (excluding dates)
        new_entities = [e for e in entities if not e.next_to_same_type]
        return new_entities

    def merge_overlapping_entities(self, entities):
        """ Merge overlapping entities. """
        assert isinstance(entities, list) # list of Entity
        
        # figa should always return the longest match first
        last_entity = None
        last_entity_offset = set()
        new_entities = []
        for current_entity in entities:
            current_entity_offset = set(range(current_entity.start_offset, current_entity.end_offset + 1))
            if last_entity_offset & current_entity_offset != set() and last_entity_offset | current_entity_offset != last_entity_offset:
                last_entity_string = last_entity.input_string[last_entity.start_offset:last_entity.end_offset]
                current_entity_string = current_entity.input_string[current_entity.start_offset:current_entity.end_offset]
                if "," in current_entity_string: # Pokud entita, jenž má být připojena k předchozí entitě kvůli překryvu, obsahuje čárku, pak je přeskočena.
                    continue
                elif "," in last_entity_string and current_entity.senses != set(): # Např. upřednostní entitu "František Stárek" zahozením entity "Staněk, František" v řetězci "Karel Srp, Dr. Vladimír Staněk, František Stárek, Dr. Jaroslav Studený, …"
                    # Předchozí entita se zkrátí dle aktuální entity a zůstane pouze jako možná koreference
                    last_entity.end_offset = current_entity.start_offset
                    last_entity_string = last_entity.input_string[last_entity.start_offset:last_entity.end_offset]
                    last_entity.end_offset -= len(last_entity_string) - len(last_entity_string.rstrip(string.whitespace + ","))
                    last_entity.senses = set()
                    # Přidání aktuální entity
                    new_entities.append(current_entity)
                    last_entity = current_entity
                    last_entity_offset = current_entity_offset
                    continue
                
                if len(last_entity.parents) == 0:
                    new_entity = copy.copy(last_entity)
                    new_entity.parents.append(last_entity)
                    new_entity.senses = set()
                    new_entity.senses.update(last_entity.senses)
                    last_entity = new_entity
                    new_entities[-1] = last_entity
                last_entity.parents.append(current_entity)
                last_entity.start_offset = min(last_entity.start_offset, current_entity.start_offset)
                last_entity.end_offset = max(last_entity.end_offset, current_entity.end_offset)
                last_entity_offset = set(range(last_entity.start_offset, last_entity.end_offset + 1))
                last_entity.senses.update(current_entity.senses)
            else:
                new_entities.append(current_entity)
                last_entity = current_entity
                last_entity_offset = current_entity_offset
        return new_entities

    def recognize(self, input_string, print_all=False, print_result=True, print_uri=False, print_score=False, lowercase=False, remove=False, split_interval=True, find_names=False, entities_overlap=False):
        """
        Prints a list of entities found in input_string.

        print_all - if false, all entities are disambiguated
        print_result - if True, the result is both returned as a list of entities and printed to stdout; otherwise, it is only returned
        print_uri - print an URI instead of a line number of the KB
        print_score - similar to print_all, but also prints the score for each entity alternative
        lowercase - the input string is lowercased
        remove - removes accent from the input string
        split_interval - split dates intervals in function dates.find_dates()
        entities_overlap - enable overlapping of entities in output from Figa
        """
        assert isinstance(input_string, str)
        assert isinstance(print_all, bool)
        assert isinstance(print_result, bool)
        assert isinstance(print_uri, bool)
        assert isinstance(print_score, bool)
        assert isinstance(lowercase, bool)
        assert isinstance(remove, bool)
        assert isinstance(split_interval, bool)
        assert isinstance(find_names, bool)
        
        kb = self.kb
        
        class DebugChangesInEntities():
            def __init__(self):
                self.last_status_of_entities = None
            
            def check(self, entities, responsible_line):
                if debug.DEBUG_EN:
                    if self.last_status_of_entities is not None:
                        new_status_of_entities = self.getStatusOfEntities(entities)
                        diff = "".join(difflib.unified_diff(self.last_status_of_entities, new_status_of_entities, fromfile='before', tofile='after', n=0))[:-1]
                        if diff:
                            print_dbg_en(responsible_line, diff, delim="\n", stack_num=2)
                        self.last_status_of_entities = new_status_of_entities
                    else:
                        self.last_status_of_entities = self.getStatusOfEntities(entities)
            
            def getStatusOfEntities(self, entities):
                return [e+"\n" for e in map(lambda e: e.to_string(display_uri=e.display_uri, display_score=e.display_score, debug=debug.DEBUG_EN) if isinstance(e, Entity) else str(e), sorted(entities, key=lambda ent: ent.start_offset))]
        debugChangesInEntities = DebugChangesInEntities().check
        
        # replacing non-printable characters with space characters
        input_string = re.sub("[\x01-\x08\x0e-\x1f\x0c\x7f]", " ", input_string)

        # running with parametr --remove_accent
        if remove:
            input_string = remove_accent(input_string)

        # creating entity register
        register = EntityRegister()
        # a set of all possible senses
        global_senses = set()

        # getting entities from figa
        figa_entities, figa_raw_output = self.get_entities_from_figa(kb, input_string, lowercase, global_senses, register, print_score, print_uri, entities_overlap=entities_overlap)
        debugChangesInEntities(figa_entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))
        print_dbg("        # Output from Figa:\n\n", figa_raw_output, delim="")

        # retaining only possible coreferences for each entity
        for e in figa_entities:
            e.partial_match_senses = e.partial_match_senses & global_senses

        # removing shorter entity from overlapping entities
        figa_entities = remove_shorter_entities(figa_entities)
        debugChangesInEntities(figa_entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

        if entities_overlap:
            # merge overlapping entities
            figa_entities = self.merge_overlapping_entities(figa_entities)
            debugChangesInEntities(figa_entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

        # removing entities without any sense
        nationalities = []
        entities = []
        for e in figa_entities:
            if e.is_nationality:
                nationalities.append(e)
            elif e.senses or e.partial_match_senses or e.source.lower() in self.ner_vars.PRONOUNS:
                entities.append(e)
        debugChangesInEntities(entities, "removing entities without any sense")

        # searches for dates and intervals in the input
        dates_and_intervals = self.dates.find_dates(input_string, split_interval=split_interval)

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
        name_coreferences = [e for e in entities if e.source.lower() not in self.ner_vars.PRONOUNS and not e.source.lower().startswith("the ")]
        self.resolve_coreferences(name_coreferences, context, print_all, register) # Zde se ověřuje, zda-li části jmen jsou odkazy nebo samostatné entity.
        debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))
        self.resolve_coreferences(entities, context, print_all, register) # Dle předchozích kroků se dosadí správné odkazy.
        debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

        # resolving overlapping entities and proper nouns
        entities = self.resolve_overlapping_proper_nouns(entities, input_string)
        debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

        # determining whether two entities lie next to each other
        entities = set(self.remove_nearby_entities(kb, entities, input_string))
        debugChangesInEntities(entities, linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-1))

        # updating entities_and_dates
        entities_and_dates = [e for e in entities_and_dates if isinstance(e, self.dates.Date) or e in entities]
        debugChangesInEntities(entities_and_dates, "updating entities_and_dates")

        # finding unknown names
        if find_names:
            self.add_unknown_names(kb, entities_and_dates, input_string, register, figa_raw_output=figa_raw_output)

        # omitting entities without a sense
        if entities_and_dates:
            if not (print_all or print_score):
                entities_and_dates = [e for e in entities_and_dates if isinstance(e, self.dates.Date) or e.has_preferred_sense() or e.is_name]
            else:
                if print_all:
                    for e in entities_and_dates:
                        if isinstance(e, Entity):
                            e.set_preferred_sense(None)
                entities_and_dates = [e for e in entities_and_dates if isinstance(e, self.dates.Date) or (e.is_coreference and e.partial_match_senses) or (not e.is_coreference and e.senses) or e.is_name]
        debugChangesInEntities(entities_and_dates, "omitting entities without a sense")

        if print_result:
            print("\n".join(map(str, entities_and_dates)))

        return entities_and_dates

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

def remove_shorter_entities(entities):
    """ Removing shorter entity from overlapping entities. """
    assert isinstance(entities, list) # list of Entity

    # figa should always return the longest match first
    max_end_offset = -1
    new_entities = []
    for e in entities:
        if e.end_offset > max_end_offset:
            new_entities.append(e)
            max_end_offset = e.end_offset
    return new_entities

def main():
    # argument parsing
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--all', action='store_true', default=False, dest='all', help='Prints all entities without disambiguation.')
    group.add_argument('-s', '--score', action='store_true', default=False, dest='score', help='Prints all possible senses with respective score values.')
    parser.add_argument('-q', '--lang', default = 'en', help='Language of recognition / disambiguation.')
    parser.add_argument('-d', '--daemon-mode', action='store_true', default=False, help='Runs ner.py in daemon mode.')
    parser.add_argument('-f', '--file',  help='Uses a given file as as an input.')
    parser.add_argument('-r', '--remove-accent', action='store_true', default=False, help="Removes accent in input.")
    parser.add_argument('-l', '--lowercase', action='store_true', default=False, help="Changes all characters in input to the lowercase characters.")
    parser.add_argument('-n', '--names', action='store_true', default=False, help="Recognizes and prints all names with start and end offsets.")
    parser.add_argument('--overlap', action='store_true', default=False, help="Enable overlapping of entities in output from Figa.")
    parser.add_argument("--own_kb_daemon", action="store_true", dest="own_kb_daemon", help=("Run own KB daemon although another already running."))
    parser.add_argument("--debug", action="store_true", help="Enable debugging reports.")
    parser.add_argument("--uri", action="store_true", help="Print an URI instead of a line number of the KB.")
    
    arguments = parser.parse_args()
    
    arguments.lang = arguments.lang.lower()
    if arguments.lang not in LANGS_ALLOWED:
        raise RuntimeError(f'Language "{arguments.lang}" is not supported yet.')
    
    if not debug.DEBUG_EN and arguments.debug:
        debug.DEBUG_EN = True
        
    
    # allowed tokens for daemon mode
    tokens = set(["NER_NEW_FILE", "NER_END", "NER_NEW_FILE_ALL", "NER_END_ALL", "NER_NEW_FILE_SCORE", "NER_END_SCORE", "NER_NEW_FILE_NAMES", "NER_END_NAMES"])
    
    # init main unit
    ner = Ner(arguments.lang, own_kb_daemon=arguments.own_kb_daemon)
    ner.start()

    if arguments.daemon_mode:
        input_string = ""
        while True:
            line = sys.stdin.readline().rstrip()
            if line in tokens:
                if "ALL" in line:
                    ner.recognize(input_string, print_all=True, lowercase=arguments.lowercase, remove=arguments.remove_accent, print_uri=arguments.uri, entities_overlap=arguments.overlap)
                elif "SCORE" in line:
                    ner.recognize(input_string, print_score=True, lowercase=arguments.lowercase, remove=arguments.remove_accent, print_uri=arguments.uri, entities_overlap=arguments.overlap)
                elif "NAMES" in line:
                    ner.recognize(input_string, find_names=True, lowercase=arguments.lowercase, remove=arguments.remove_accent, print_uri=arguments.uri, entities_overlap=arguments.overlap)
                else:
                    ner.recognize(input_string, print_all=False, lowercase=arguments.lowercase, remove=arguments.remove_accent, print_uri=arguments.uri, entities_overlap=arguments.overlap)
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
        input_string = input_string.rstrip()
        ner.recognize(input_string, print_all=arguments.all, print_score=arguments.score, lowercase=arguments.lowercase, remove=arguments.remove_accent, find_names=arguments.names, print_uri=arguments.uri, entities_overlap=arguments.overlap)

if __name__ == "__main__":
    main()
