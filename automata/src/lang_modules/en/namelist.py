#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Set

from automata.src.namelist import Namelist as ParentClass


class Namelist(ParentClass):
    def _get_lang_unwanted_matches(self) -> Set[str]:
        return set(["from", "Prince"])

    def _get_person_lang_unwanted_start_matches(self) -> Set[str]:
        return set(["List of "])

    def _get_saint_variants(self) -> Set[str]:
        return set(
            [
                "Saint",
                "Holy",
            ]
        )

    def _get_saint_abb(self) -> str:
        return "St"
