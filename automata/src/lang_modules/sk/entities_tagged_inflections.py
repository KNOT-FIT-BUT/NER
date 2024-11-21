#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from automata.src.entities_tagged_inflections import EntitiesTaggedInflections as ParentClass


class EntitiesTaggedInflections(ParentClass):
    def __init__(self) -> None:
        self.lang = "sk"

    def get_process_command(self) -> str:
        return self._process_namegen()
