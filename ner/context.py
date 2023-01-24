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
#

import sys
sys.path.append("..")

import numpy
from . import entity as modEntity
from . import ner_knowledge_base as base_ner_knowledge_base
from .configs import KB_MULTIVALUE_DELIM
from libs import dates


class Context(object):
    """ Information about a context of a processed text. """

    def __init__(self, entities, kb, paragraphs, nationalities):
        """ Prepares the context from the list of entities disambiguated without the context. """
        assert isinstance(entities, list) # list of Entity and dates.Date
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(paragraphs, list)

        self.entities = entities
        self.kb = kb
        self.paragraphs = paragraphs

        # max score for each candidate
        self.people_max_scores = {}
        # number of locations in each country mentioned in each paragraph (+ sorted version)
        self.mentions = {}
        self.countries = {}
        self.country_sum = {}
        self.countries_sorted = {}
        # people mentioned by full name in whole text
        self.people_in_text = set()
        # people mentioned by full name in paragraph
        #self.people = {}
        self.organisations = {}
        # list of nationalities mentioned in each paragraph (may contain duplicates)
        self.people_nationalities = {}
        # list of dates mentioned in each paragraph (may contain duplicates)
        self.people_dates = {}
        # list of proffesions mentioned in paragraph
        self.people_professions = {}
        # initializing pronoun variables
        self.init_pronouns()
        # initializing the paragraph index
        self.paragraph_index = 0
        self.events = {}

        # initializing index variables
        par_index = 0
        ent_index = 0
        nat_index = 0

        # adding one artificial paragraph, otherwise self.paragraphs[par_index + 1] will fail
        self.paragraphs.append(sys.maxsize)

        # computing statistics for each paragraph
        for par in self.paragraphs:
            self.mentions[par] = {}
            self.countries[par] = {}
            self.people_nationalities[par] = []
            self.people_dates[par] = []
            #self.people[par] = {}
            self.events[par] = {}
            self.country_sum[par] = 0
            self.people_professions[par] = []
            self.organisations[par] = {}
            par_text = ""

            while (nat_index < len(nationalities) and nationalities[nat_index].start_offset < self.paragraphs[par_index + 1]):
                nat = nationalities[nat_index]
                name = nat.source
                if name not in self.people_nationalities[par]:
                    self.people_nationalities[par].append(name)

                nat_index += 1

            while (ent_index < len(entities) and entities[ent_index].start_offset < self.paragraphs[par_index + 1]):
                ent = self.entities[ent_index]

                if isinstance(ent, modEntity.Entity):
                    par_text = ent.input_string[self.paragraphs[par_index] : self.paragraphs[par_index + 1]]
                    ent.begin_of_paragraph = par

                    # entities with only 1 candidate
                    if not ent.poorly_disambiguated:
                        ent_type_set = ent.kb.get_ent_type(ent.get_preferred_sense())
                        for ent_type in ent_type_set:
                            if ent_type not in self.mentions[par]:
                                self.mentions[par][ent_type] = {}

                        if 'geo' in ent_type_set:
                            # get location country name and aliases
                            name = ent.kb.get_data_for(ent.get_preferred_sense(), "NAME")
                            country = ent.kb.get_data_for(ent.get_preferred_sense(), "COUNTRY")

                            if name not in self.mentions[par][ent_type]:
                                self.mentions[par][ent_type][name] = 1
                            else:
                                self.mentions[par][ent_type][name] += 1
                            self.country_sum[par] += 1

                            if country:
                                if country not in self.mentions[par][ent_type]:
                                    self.mentions[par][ent_type][country] = 1
                                else:
                                    self.mentions[par][ent_type][country] += 1
                                self.country_sum[par] += 1
                        # if entity is person update number of her mentions in dictionary
                        else:
                            name = ent.kb.get_data_for(ent.get_preferred_sense(), "NAME")

                            if name not in self.mentions[par][ent_type]:
                                self.mentions[par][ent_type][name] = 0
                            self.mentions[par][ent_type][name] += 1

                    elif ent.has_preferred_sense():
                        for c in ent.candidates:
                            ent_type_set = ent.kb.get_ent_type(c)
                            if 'person' in ent_type_set:
                                professions = ent.kb.get_data_for(c, "ROLES")
                                if professions:
                                    professions = professions.split(KB_MULTIVALUE_DELIM)
                                    [self.people_professions[par].append(p) for p in professions if par_text.find(p) != -1 and p not in self.people_professions[par]]

                elif isinstance(ent, dates.Date):
                    # removing days and possibly months with zeros (only non-zeros will remain)
                    if ent.class_type == ent.Type.DATE:
                        self.people_dates[par].append(ent.iso8601.showWithoutZeros())
                    elif ent.class_type == ent.Type.INTERVAL:
                        self.people_dates[par].append(ent.date_from.showWithoutZeros())
                        self.people_dates[par].append(ent.date_to.showWithoutZeros())

                ent_index += 1
            par_index += 1

        # removing the artificial paragraph
        self.paragraphs.pop()

    def recompute_paragraph_offset(self, start_offset):
        """
        Recomputes paragraph offset, if the entity at the start_offset belongs
        to the different paragraph.
        """
        assert isinstance(start_offset, int)

        # we are in the last paragraph -> no change in paragraph offsets
        if self.paragraph_index + 1 >= len(self.paragraphs):
            return
        # the entity belongs to the current paragraph -> no change in paragraph offsets
        elif start_offset >= self.paragraphs[self.paragraph_index] and start_offset < self.paragraphs[self.paragraph_index + 1]:
            return
        # the entity belongs to the different paragraph -> we have to recompute paragraph offsets
        else:
            par_i = self.paragraph_index
            while par_i + 1 < len(self.paragraphs) and self.paragraphs[par_i + 1] <= start_offset:
                par_i += 1
            self.paragraph_index = par_i

    def update(self, entity):
        """ Updates context (last person, last male, last female, last location etc.). """
        assert isinstance(entity, modEntity.Entity)

        # keep the last entity of each pronoun type for pronoun coreference resolution
        ent_type_set = self.kb.get_ent_type(entity.get_preferred_sense())

        if 'person' in ent_type_set:
            self.before_last_person = self.last_person
            self.last_person = entity
            gender = self.kb.get_data_for(entity.get_preferred_sense(), "GENDER")
            if gender == 'M':
                self.last_male = entity
                self.last_unknown_gender = None
            elif gender == 'F':
                self.last_female = entity
                self.last_unknown_gender = None
            else:
                self.last_unknown_gender = entity
        elif "location" in ent_type_set:
            self.last_location = entity
        else:
            self.last_thing = entity

    def mentioned_in_par(self, candidates, field):
        par_index = self.paragraphs[self.paragraph_index]

        mentioned_in_par_score = 0
        if field in self.mentions[par_index]:
            for c in candidates:
                if c in self.mentions[par_index][field]:
                    mentioned_in_par_score =  self.mentions[par_index][field][c]
                    break

        if mentioned_in_par_score:
            mentioned_in_par_score = mentioned_in_par_score * 100 / sum(self.mentions[par_index][field].values())

        return mentioned_in_par_score


    def person_percentile(self, candidate):
        """
        Returns a percentile of references to a candidate person from
        knowledge base amongst other people.
        """
        assert isinstance(candidate, int)
        par_index = self.paragraphs[self.paragraph_index]

        # computing people_nation_score
        people_nationality_score = 0
        # getting the nationality for a given person
        person_nationalities = self.kb.get_nationalities(candidate)
        for nat in self.people_nationalities[self.paragraphs[self.paragraph_index]]:
            if nat in person_nationalities:
                # the person has the same nationality like other persons in this paragraph
                people_nationality_score += 1

        if self.people_nationalities[par_index]:
           # normalizing people_nationality_score
           people_nationality_score = people_nationality_score * 100 / len(self.people_nationalities[par_index])

        # computing people_date_score
        people_date_score = 0
        # getting the dates for a given person
        person_dates = self.kb.get_dates(candidate)
        for context_date in self.people_dates[par_index]:
            for person_date in person_dates:
                if context_date.find(person_date) > -1 or person_date.find(context_date) > -1:
                    # the person has the date mentioned in this paragraph
                    people_date_score += 1
        if self.people_dates[par_index]:
           # normalizing people_date_score
            people_date_score = people_date_score * 100 / len(self.people_dates[par_index])

        # computing people_profession_score
        people_profession_score = 0

        person_professions = self.kb.get_data_for(candidate, "ROLES").split(KB_MULTIVALUE_DELIM)
        for prof in person_professions:
            if prof in self.people_professions[par_index]:
                people_profession_score += 1
        if self.people_professions[par_index]:
            people_profession_score = people_profession_score * 100 / len(self.people_professions[par_index])


        person_name = [self.kb.get_data_for(candidate, "NAME")]
        mentioned_in_par_score = self.mentioned_in_par(person_name, 'person')

        # summing up the scores
        result = numpy.average([people_nationality_score, people_date_score, people_profession_score, mentioned_in_par_score])

        # storing new max score
        if candidate in self.people_max_scores and result > self.people_max_scores[candidate]:
                self.people_max_scores[candidate] = result
        else:
            self.people_max_scores[candidate] = result

        return result

    def country_percentile(self, country):
        """ Returns a percentile of a number of location belonging to a country identified by code. """
        assert isinstance(country, str)
        
        if country not in self.countries[self.paragraphs[self.paragraph_index]]:
            # we don't have any statistics for a given country
            return 0
        else:
            # computing and normalizing score for a given country
            return self.countries[self.paragraphs[self.paragraph_index]][country] * 100 / sum(self.countries[self.paragraphs[self.paragraph_index]].values())
    def common_percentile(self, candidate, ent_type):
        name = [self.kb.get_data_for(candidate, "NAME")]
        mentioned_in_par_score = self.mentioned_in_par(name, ent_type)

        return mentioned_in_par_score


    def org_event_percentile(self, candidate, ent_type):
        par_index = self.paragraphs[self.paragraph_index]

        name = [self.kb.get_data_for(candidate, "NAME")]
        mentioned_in_par_score = self.mentioned_in_par(name, ent_type)

        place = [self.kb.get_data_for(candidate, "LOCATION")]
        place_score = self.mentioned_in_par(place, 'settlement')

        org_date_score = 0
        if ent_type == "organisation":
            org_dates = [self.kb.get_data_for(candidate, "FOUNDED"), self.kb.get_data_for(candidate, "CANCELLED")]
        else:
            org_dates = [self.kb.get_data_for(candidate, "START"), self.kb.get_data_for(candidate, "END")]

        for context_date in self.people_dates[par_index]:
            for org_date in org_dates:
                if context_date and org_date and (context_date.find(org_date) > -1 or org_date.find(context_date) > -1):
                    # the person has the date mentioned in this paragraph
                    org_date_score += 1
        if self.people_dates[par_index]:
            # normalizing people_date_score
            org_date_score = org_date_score * 100 / len(self.people_dates[par_index])


        result = numpy.average([mentioned_in_par_score, place_score, org_date_score])

        return result


    def init_pronouns(self):
        """ Initializes pronoun variables. """

        self.before_last_person = None
        self.last_person = None
        self.last_male = None
        self.last_female = None
        self.last_unknown_gender = None
        self.last_thing = None
        self.last_location = None
        self.before_last_male = None
        self.before_last_female = None
