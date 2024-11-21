#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Tomáš Volf, ivolf@fit.vut.cz

import logging

from typing import Dict, Set


debug_mode = True

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s]:   %(message)s",
    level=logging.DEBUG if debug_mode else logging.WARNING,
)


class DictTools:
    @staticmethod
    def add_to_dict_key(dictionary: Dict, key: str, items: Set):
        if key not in dictionary:
            dictionary[key] = items
        else:
            dictionary[key] |= items

    @classmethod
    def add_to_dict(cls, dictionary: Dict, added_dict: Dict):
        for k, v in added_dict.items():
            cls.add_to_dict_key(dictionary=dictionary, key=k, items=v)
