#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from ...word_types import WordTypes as BaseWordTypes

class WordTypes(BaseWordTypes):
    # pronouns along with their type they refer to
    PRONOUNS = {
        "on"  : "M",
        "jeho": "M",
        "neho": "M",
        "jemu": "M",
        "nemu": "M",
        "mu"  : "M",
        "ho"  : "M",
        "ňom" : "M",
        "ním" : "M",

        "ona" : "F",
        "jej" : "F",
        "nej" : "F",
        "ju"  : "F",
        "ňu"  : "F",
        "ňou" : "F",
    }

    PROPER_NOUNS_PREPS = set()

    VERBS = {" bol ", " bola ", " je "}
