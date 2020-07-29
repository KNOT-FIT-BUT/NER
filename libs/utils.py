#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Author: Tomáš Volf, ivolf[at]fit.vutbr.cz

import logging
import re
import unicodedata


# a regex matching unwanted strings in unicode charaters names
ACCENT_REGEX = re.compile(r"COMBINING|HANGUL JUNGSEONG|HANGUL JONGSEONG")

def remove_accent(_string):
    """Removes accents from a string. For example, Eduard Ovčáček -> Eduard Ovcacek."""
    nkfd_form = unicodedata.normalize('NFKD', _string)
    return "".join([c for c in nkfd_form if not unicodedata.combining(c)])


def remove_accent_unicode(_string):
    """ Removes accents from a string. For example, "Eduard Ovčáček" -> "Eduard Ovcacek". """
    assert isinstance(_string, str)

    nfkd_form = unicodedata.normalize('NFKD', _string)
    result = "".join([c for c in nfkd_form if not ACCENT_REGEX.search(unicodedata_name(c))])
    if len(_string) == len(result):
        return result
    else:
        return _string

def ncr2unicode(s):
    """
    Translates hexadecimal NCRs (https://en.wikipedia.org/wiki/Numeric_character_reference) to the Unicode. For example, '&#x957F;&#x5EA6;' (??) -> '\xe9\x95\xbf\xe5\xba\xa6' (utf-8).
    """
    def replaceEntities(s):
        s = s.groups()[0]
        try:
            if s[0] in ['x','X']:
                c = int(s[1:], 16)
            else:
                c = int(s)
            return chr(c)
        except ValueError:
            return '&#'+s+';'

    return re.sub(r"&#([xX]?(?:[0-9a-fA-F]+));", replaceEntities, s)

    
def unicodedata_name(c):
    """ Workaround for unicodedata.name(c) in order to deal with ValueError reising for characters without names (all control characters)."""

    try:
        return unicodedata.name(c)
    except ValueError:
        return ""


def get_ner_logger():
    module_logger = logging.getLogger("ner")
    #module_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(name)s: %(context)s:\n'''\n%(message)s\n'''")
    console_handler.setFormatter(formatter)
    module_logger.addHandler(console_handler)
    
    return module_logger
