#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# <LOKÁLNÍ IMPORTY>
from ...ner_vars import NerVars as BaseNerVars
# </LOKÁLNÍ IMPORTY>

class NerVars(BaseNerVars):
    # pronouns along with their type they refer to
    PRONOUNS = {
        "on"  : "M",
        "ho"  : "M",
        "jej" : "M",
        "něj" : "M",
        "jeho": "M",
        "něho": "M",
        "mu"  : "M",
        "jemu": "M",
        "němu": "M",
        "něm" : "M",
        "jím" : "M",
        "ním" : "M",
        
        "ona" : "F",
        "jí"  : "F",
        "ní"  : "F",
        "ji"  : "F",
        "ni"  : "F",
    }

    PROPER_NOUNS_PREPS = set()

    VERBS = {" byl ", " byla ", " je "} # <entity> <verb> <explanation of entity>
