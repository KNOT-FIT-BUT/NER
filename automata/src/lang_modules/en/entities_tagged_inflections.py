#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from automata.src.entities_tagged_inflections import EntitiesTaggedInflections as ParentClass


class EntitiesTaggedInflections(ParentClass):
    def set_lang(self) -> None:
        self.lang = "en"

    def get_process_command(self) -> str:
        return ""
