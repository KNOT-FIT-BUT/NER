#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC

class NerVars(ABC):
    def __init__(self, lang):
        pass
    
    # pronouns along with their type they refer to
    PRONOUNS = NotImplemented
    PROPER_NOUNS_PREPS = NotImplemented
    VERBS = NotImplemented
