#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# <LOKÁLNÍ IMPORTY>
from ...ner_vars import NerVars as BaseNerVars
# </LOKÁLNÍ IMPORTY>

class NerVars(BaseNerVars):
    # pronouns along with their type they refer to
    PRONOUNS = {
            "he" : "M",
           "him" : "M",
       "himself" : "M",
           "his" : "M",
           "she" : "F",
           "her" : "F",
          "hers" : "F",
       "herself" : "F",
           "who" : "MF",
          "whom" : "MF",
         "whose" : "MF",
          "here" : "L",
         "there" : "L",
         "where" : "L"
    }
    
    PROPER_NOUNS_PREPS = set(['the', 'upon'])
    
    VERBS = {" is ", " are ", " was ", " were "}
