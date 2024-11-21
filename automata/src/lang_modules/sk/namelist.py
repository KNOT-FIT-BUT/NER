#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Set

from automata.src.namelist import Namelist as ParentClass


class Namelist(ParentClass):
    def _get_lang_unwanted_matches(self) -> Set[str]:
        return set(["z", "Princ"])

    def _get_person_lang_unwanted_start_matches(self) -> Set[str]:
        return set(["Zoznam "])

    def _get_saint_variants(self) -> Set[str]:
        return set(
            [
                "Svätý",
                "Svätého",
                "Svätému",
                "Svätom",
                "Svätým",
                "Svätá",
                "Svätej",
                "Svätú",
                "Svätou",
                "Svätí",
                "Svätých",
                "Svätým",
                "Svätými",
            ]
        )

    def _get_saint_abb(self) -> str:
        return "Sv"
