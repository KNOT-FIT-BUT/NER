#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Tomáš Volf, ivolf@fit.vut.cz

import logging

from json import dump as jdump, load as jload
from os.path import getsize, isfile
from pickle import dump as pdump, load as pload
from typing import Set

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s]:   %(message)s",
    level=logging.DEBUG
)


def are_files_with_content(paths: Set[str]) -> bool:
    for path in paths:
        if not is_file_with_content(path):
            return False
    return True


def is_file_with_content(path: str) -> bool:
    return isfile(path) and getsize(path)


def json_dump(data, fpath: str) -> None:
    if not data:
        if not data:
            logging.warning(f'Can not save "{fpath}" due to empty data.')
        return
    with open(fpath, "w", encoding="utf8") as f:
        jdump(data, f, default=_json_dump_default, ensure_ascii=False)


def json_load(fpath: str):
    with open(fpath, "r", encoding="utf8") as f:
        return jload(f)


def pickle_dump(data, fpath: str) -> None:
    if not data:
        if not data:
            logging.warning(f'Can not save "{fpath}" due to empty data.')
        return
    with open(fpath, "wb") as f:
        pdump(data, f)


def pickle_load(fpath: str):
    with open(fpath, "rb") as f:
        return pload(f)


def _json_dump_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError
