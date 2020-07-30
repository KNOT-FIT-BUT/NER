#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

# <LOKÁLNÍ IMPORTY>
from . import ner_knowledge_base as base_ner_knowledge_base
from . import context as modContext
from . import entity_register
from .configs import KB_MULTIVALUE_DELIM # !!! jen CZ addons
from .ner_loader import NerLoader
from ..libs.nationalities.nat_loader import NatLoader
from ..libs.utils import ncr2unicode, remove_accent_unicode, get_ner_logger
from ..name_recognizer import data_row as module_data_row

from . import debug
debug.DEBUG_EN = False
from .debug import cur_inspect
# </LOKÁLNÍ IMPORTY>

module_logger = get_ner_logger()

class Entity(ABC):
    """ A text entity referring to a knowledge base item. """

    def __init__(self, lang):
        self.lang = lang
        
        self.next_to_same_type = False
        self.display_score = False
        self.display_uri = False
        self.poorly_disambiguated = True
        self.is_coreference = False
        self.is_name = False
        self.is_nationality = False

        self.preferred_sense = None
        self.next_word_begin = None
        self.next_word_end = None
        self.previous_word = None
        self.before_previous = None
        self.candidates = []
        self.score = []
        self.static_score = []
        self.context_score = []
        self.coreferences = set()
        self.ner_vars = NerLoader.load(module = "ner_vars", lang = self.lang, initiate = "NerVars")


    def create(self, entity_attributes, kb, input_string, register):
        """
        Creates an entity by parsing a line of figa output from entity_str.
        Entity will be referring to an item of the knowledge base kb.

        entity_attributes - entity data from figa
        kb - Knowledge Base
        input_string - input string in Unicode
        register - entity register
        """
        #assert isinstance(entity_attributes, FigaOutput)
        assert type(entity_attributes).__name__ == "FigaOutput"
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(input_string, str)
        assert isinstance(register, entity_register.EntityRegister)

        self.input_string = input_string
        self.input_string_bytes = input_string.encode()

        self.kb = kb
        self.register = register

        # getting possible senses (sense 0 marks a coreference)
        self.senses = set([s for s in entity_attributes.kb_rows if s != 0])

        # Ofsety jsou vztaženy k unicode.
        self.start_offset = entity_attributes.start_offset
        self.end_offset = entity_attributes.end_offset
        self.begin_of_paragraph = None

        # the source text of the entity
        self.source = ncr2unicode(entity_attributes.fragment)

        if len(self.senses) == 0:
            nationalities_forms = NatLoader.load(self.lang).get_nationalities() # !!!
            if self.source in nationalities_forms:
                self.is_nationality = True

        # possible coreferences - people whose names are supersets of an entity
        self.partial_match_senses = self.kb.people_named(remove_accent_unicode(self.source).lower())

    @classmethod
    def from_data_row(cls, kb, dr, input_string, register):
        assert isinstance(kb, base_ner_knowledge_base.KnowledgeBase)
        assert isinstance(dr, module_data_row.DataRow)
        assert isinstance(input_string, str)
        assert isinstance(register, entity_register.EntityRegister)
        
        input_string_bytes = input_string.encode()

        entity = cls(str(dr).split('\t'), kb, input_string, input_string_bytes, register)
        entity.is_name = True
        return entity

    def set_preferred_sense(self, _sense):
        assert isinstance(_sense, (int, Entity)) or _sense == None

        if debug.DEBUG_EN: # TODO: Toto si ještě musím promyslet.
            if self.preferred_sense == _sense:
                module_logger.debug("self.preferred_sense == _sense", extra={"context": cur_inspect()})
            if self.get_preferred_sense() == _sense:
                module_logger.debug("self.get_preferred_sense() == _sense", extra={"context": cur_inspect()})
        
        self.preferred_sense = _sense

        if not isinstance(_sense, Entity):
            self.register.insert_entity(self, _sense)

    def has_preferred_sense(self):
        return self.preferred_sense

    def get_preferred_sense(self):
        if isinstance(self.preferred_sense, Entity):
            return self.preferred_sense.preferred_sense
        else:
            return self.preferred_sense

    def get_preferred_entity(self):
        if not isinstance(self.preferred_sense, Entity):
            return self
        else:
            return self.preferred_sense

    @abstractmethod
    def apply_lang_depended_sense_rules(self):
        raise NotImplementedError

    def disambiguate_without_context(self):
        """ Chooses the correct sense of the entity as the preferred one (without context). """

        # we don't resolve coreference in this step
        if self.source.lower() in self.ner_vars.PRONOUNS or self.partial_match_senses:
            self.is_coreference = True
            return

        self.apply_lang_depended_sense_rules()

        # if candidates contain any artist, excludes all groups # NOTE: To proč? Je to ze statistiky nebo tím, že nás to více zajímá?
        for sense in self.senses:
            ent_type_set = self.kb.get_ent_type(sense)
            if "artist" in ent_type_set:
                self.senses = [s for s in self.senses if not self.kb.get_ent_type(s) & {"group"}]
                break

        # search for one of verbs in rest of the sentence
        sentence = self.right_sentence()
        verb_index = -1
        for verb in self.ner_vars.VERBS:
            verb_index = sentence.find(verb)
            if(verb_index != -1):
                break

        # if verb is behind entity in sentence try to disambiguate
        # Example: sentence: Washington byl první prezident USA.
        #          possible entities: George Washington - person
        #                             Washington D. C. - location
        #          verb after entity - byl
        #          proffesion mentioned after verb - prezident
        #          Location entity eliminated
        if(verb_index != -1):
            proffesions = []
            for s in self.senses:
                if "person" in self.kb.get_ent_type(s):
                    proffesions = self.kb.get_data_for(s, "ROLES")
                    if(proffesions):
                        proffesions = proffesions.split(KB_MULTIVALUE_DELIM)
                        proffesions = [p for p in proffesions if sentence.find(" " + p + " ", verb_index) != -1]
                        if(proffesions):
                            break

            if(proffesions):
                new_senses = []
                for s in self.senses:
                    if "person" in self.kb.get_ent_type(s):
                        for proffesion in self.kb.get_data_for(s, "ROLES").split(KB_MULTIVALUE_DELIM):
                            if(proffesion in proffesions):
                                new_senses.append(s)
                                break
                self.senses = new_senses

        self.senses = set(self.senses)
        self.candidates = list(self.senses)


        # entity doesn't have any candidates
        if not self.candidates:
            return
        # entity has exactly one candidate
        elif len(self.candidates) == 1:
            self.set_preferred_sense(self.candidates[0])
            self.poorly_disambiguated = False

        # the entity has to be disambiguated
        if not self.has_preferred_sense():
            for i in self.candidates:
                static_score = self.kb.get_score(i)
                self.static_score.append(static_score)
                self.score.append(static_score)

            self.set_preferred_sense(self.candidates[self.score.index(max(self.score))])

    def disambiguate_with_context(self, context):
        """ Chooses the correct sense of the entity as the preferred one (with context). """
        assert isinstance(context, modContext.Context)

        # we don't resolve coreference in this step
        if self.is_coreference or not self.candidates:
            return

        # recomputing paragraph offset
        context.recompute_paragraph_offset(self.start_offset)

        # the entity has to be disambiguated
        self.score = []
        self.static_score = []
        self.context_score = []

        for i in self.candidates:
            ent_type_set = self.kb.get_ent_type(i)
            static_score = self.kb.get_score(i)
            context_score = 0
            # !!! TODO: merge location and geo? is it realy 'geo'?
            if ent_type_set & {"geographical", "location"}:
                context_score = context.country_percentile(self.kb.get_data_for(i, "COUNTRY"))
            elif 'person' in ent_type_set:
                context_score = context.person_percentile(i)
            elif 'organisation' in ent_type_set or 'event' in ent_type_set:
                context_score = context.org_event_percentile(i, ent_type_set)
            else:
                context_score = context.common_percentile(i, ent_type_set)

            if context_score > 0:
                self.poorly_disambiguated = False
            self.static_score.append(static_score)
            self.context_score.append(context_score)
            self.score.append(static_score + context_score)

        self.set_preferred_sense(self.candidates[self.score.index(max(self.score))])

        # if preffered sense for entity is person, increase number of mentions of that person in paragraph
        ent_type_set = self.kb.get_ent_type(self.get_preferred_sense())
        if 'person' in ent_type_set and len(self.candidates) != 1:
            name = self.kb.get_data_for(self.get_preferred_sense(), "NAME")
            if 'person' not in context.mentions[context.paragraphs[context.paragraph_index]]:
                context.mentions[context.paragraphs[context.paragraph_index]]['person'] = {}
            if name not in context.mentions[context.paragraphs[context.paragraph_index]]['person']:
                context.mentions[context.paragraphs[context.paragraph_index]]['person'][name] = 0

            context.mentions[context.paragraphs[context.paragraph_index]]['person'][name] += 1


    def is_location_coreference(self):
        return False


    def resolve_pronoun_coreference(self, context):
        """ Resolves a pronoun coreference using context. """
        assert isinstance(context, modContext.Context)
        
        if self.is_location_coreference():
            module_logger.info("Jump behind pronoun coreference %r in place %r:\"...%s...\", because his right context contains verb BE.", self.source, self.start_offset, self.input_string_in_unicode[self.start_offset-10:self.end_offset+10], extra={"context": cur_inspect()})
            return

        pronoun_type = self.ner_vars.PRONOUNS[self.source.lower()]
        # NOTE: Odtud se dějí zajímavé (až magické) věci, které nutně potřebují komentáře {
        if 'M' in pronoun_type:
            # FIXME: To níže, to je špatný HACK. (komentováno v původním anglickém kódu - trochu odlišný)
            if self.source.lower() in self.ner_vars.PRONOUNS and 'M' in self.ner_vars.PRONOUNS[self.source.lower()]:
                if context.last_unknown_gender:
                    context.before_last_male = context.last_male
                    context.last_male = context.last_unknown_gender
                    context.last_person = context.last_unknown_gender
                    context.last_unknown_gender = None
                if context.last_male and context.last_male.start_offset >= self.begin_of_paragraph:
                    self.set_preferred_sense(context.last_male.get_preferred_entity())
            else:
                # other pronoun for male
                if context.last_person:
                    #get gender of person mentioned last
                    gender = self.kb.get_data_for(context.last_person.get_preferred_sense(), "GENDER")
                    # last person mentioned - female
                    # point to last male if there is any in current paragraph
                    if gender == "F":
                        if context.last_male and context.last_male.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_male.get_preferred_entity())
                    # last person mentioned - male
                    elif gender == "M":
                        # point to before last male if there is any in current paragraph
                        if context.before_last_male and context.before_last_male.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.before_last_male.get_preferred_entity())
                        elif context.last_male.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_male.get_preferred_entity())
                    else:
                        # last person gender unknown - set to male and point to it
                        if context.last_male and not context.last_male.start_offset >= self.begin_of_paragraph:
                            context.before_last_male = context.last_male
                            context.last_male = context.last_unknown_gender
                            context.last_unknown_gender = None

                        if context.last_male and context.last_male.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_male.get_preferred_entity())


        elif 'F' in pronoun_type:
            # point to last female
            if self.source.lower() in self.ner_vars.PRONOUNS and 'F' in self.ner_vars.PRONOUNS[self.source.lower()]:
                if context.last_unknown_gender:
                    context.before_last_female = context.last_female
                    context.last_female = context.last_unknown_gender
                    context.last_person = context.last_unknown_gender
                    context.last_unknown_gender = None
                if context.last_female and context.last_female.start_offset >= self.begin_of_paragraph:
                    self.set_preferred_sense(context.last_female.get_preferred_entity())
            else:
                # other pronoun for female
                if context.last_person:
                    #get gender of person mentioned last
                    gender = self.kb.get_data_for(context.last_person.get_preferred_sense(), "GENDER")
                    # last person mentioned - male
                    # point to last female if there is any in current paragraph
                    if gender == "M":
                        if context.last_female and context.last_female.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_female.get_preferred_entity())
                    # last person mentioned - female
                    elif gender == "F":
                        # point to before last female if there is any in current paragraph
                        if context.before_last_female and context.before_last_female.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.before_last_female.get_preferred_entity())
                        elif context.last_female.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_female.get_preferred_entity())
                    else:
                        # last person gender unknown - set to female and point to it
                        if context.last_female and not context.last_female.start_offset >= self.begin_of_paragraph:
                            context.before_felast_male = context.last_female
                            context.last_female = context.last_unknown_gender
                            context.last_unknown_gender = None

                        if context.last_female and context.last_female.start_offset >= self.begin_of_paragraph:
                            self.set_preferred_sense(context.last_female.get_preferred_entity())




    def __str__(self):
        """ Converts an entity into an output format. """
        
        candidates_delim = ";" if not self.display_uri else "|"
        result = str(self.start_offset) + "\t" + str(self.end_offset) + "\t"
        if self.is_coreference:
            if self.display_uri:
                result += "uri_"
            result += "coref"
        elif self.is_name:
            result += "name"
        elif self.display_uri:
            result += "uri"
        else:
            result += "kb"
        result += "\t" + self.input_string[self.start_offset:self.end_offset].replace('\n', ' ').replace('\r', '') + "\t"
        if self.display_score and self.candidates:
            candidates_str = []
            i = 0
            for cand in self.candidates:
                cand_link = str(cand) if not self.display_uri else self.kb.get_uri(cand)
                candidates_str.append(cand_link)
                if i < len(self.score):
                    candidates_str[-1] += " " + str(self.score[i])
                i += 1
            result += candidates_delim.join(candidates_str)
        elif self.has_preferred_sense():
            result += str(self.get_preferred_sense()) if not self.display_uri else self.kb.get_uri(self.get_preferred_sense())
        else:
            if self.is_coreference:
                senses_list = sorted(self.partial_match_senses)
            else:
                senses_list = sorted(self.senses)
            for i in senses_list:
                result += str(i) if not self.display_uri else self.kb.get_uri(i)
                if i != senses_list[-1]:
                    result += candidates_delim
        return result

    def right_context(self, right):
        assert isinstance(right, str)

        length = len(right)
        text = self.input_string
        if self.end_offset + length > len(text):
            return False
        return text[self.end_offset:self.end_offset + length] == right

    def right_sentence(self): # NOT in EN
        text = self.input_string[self.end_offset:]
        collum_count = 0
        sentence = ""

        for index in range(0, len(text)):
            if(text[index] ==")"):
                collum_count -= 1
            elif(text[index] =="("):
                collum_count += 1
            elif(not collum_count):
                sentence += text[index]
                if(text[index] == "." ):
                    break
        return sentence

    def left_context(self, left):
        assert isinstance(left, str)

        length = len(left)
        text = self.input_string
        if self.start_offset - length < 0:
            return False
        return text[self.start_offset - length:self.start_offset] == left

    def is_equal(self, other):
        if self.start_offset == other.start_offset and \
        self.end_offset == other.end_offset and \
        self.source == other.source:
            return True
        return False

    def is_overlapping(self, other):
        if self.start_offset <= other.start_offset and \
        self.end_offset >= other.end_offset and \
        other.source in self.source:
            return True
        return False

    def is_person(self):
        if self.is_name:
            return True # NOTE: Je to jisté? Co města, jež se jmenují jako lidé?
        if not self.is_coreference and self.senses:
            ent_type_set = self.kb.get_ent_type(list(self.senses)[0])
            if 'person' in ent_type_set:
                return True
        return False
