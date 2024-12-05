#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright 2015 Brno University of Technology

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vut.cz
#
# Description: Creates namelist from KB.

import gc
import importlib
import logging
import regex

from argparse import ArgumentParser
from itertools import repeat
from multiprocessing import Pool
from os.path import (
    dirname,
    getmtime,
    getsize,
    isdir,
    isfile,
    join as path_join,
    realpath,
)
from pandas import to_numeric
from sys import stderr
from typing import Callable, Dict, Iterable, List, Set, Tuple, Union

from automata.src.configs import LANG_DEFAULT
from automata.src.dict_tools import DictTools
from automata.src.entities_tagged_inflections import EtiMode
from automata.src.file_utils import (
    are_files_with_content,
    is_file_with_content,
    json_dump,
    json_load,
    pickle_dump,
    pickle_load,
)
from automata.src.namelist import Namelist
from automata.src import metrics_knowledge_base
from libs.automata_variants import AutomataVariants
from libs.entities.entity_loader import EntityLoader
from libs.module_loader import ModuleLoader
from libs.utils import remove_accent


# multiple values delimiter
KB_MULTIVALUE_DELIM = metrics_knowledge_base.KB_MULTIVALUE_DELIM

URI_COLUMN_NAMES = ["WIKIPEDIA URL", "WIKIDATA URL", "DBPEDIA URL"]

SURNAME_MATCH = regex.compile(
    r"(((?<=^)|(?<=[ ]))(?:(?:da|von)(?:#[^ ]+)? )?((?:\p{Lu}\p{Ll}*(?:#[^- ]+)?-)?(?:\p{Lu}\p{Ll}+(?:#[^- ]+)?))$)"
)

# dashes variants: 0x2D (0045), 0x96 (0150), 0x97 (0151), 0xAD (0173)
DASHES = "-–—­"
RE_DASHES = regex.escape(DASHES)
RE_DASHES_VARIANTS = r"[%s]" % DASHES
RE_NAMES_SEPARATOR = r"(?: |,|\u200b|%s)" % RE_DASHES_VARIANTS

kb_struct = None
namelist = None
persons = None
UNWANTED_MATCH = None
debug_mode = True


logging.basicConfig(
    format="[%(asctime)s - %(levelname)s]:   %(message)s",
    level=logging.DEBUG if debug_mode else logging.WARNING,
)


def parse_args() -> None:
    # defining commandline arguments
    parser = ArgumentParser()
    parser.add_argument(
        "-l", "--lang", type=str, required=True, help="language to process"
    )
    parser.add_argument(
        "-d", "--lowercase", action="store_true", help="creates a lowercase list"
    )
    parser.add_argument(
        "-a",
        "--autocomplete",
        action="store_true",
        help="creates a list for autocomplete",
    )
    parser.add_argument("-u", "--uri", action="store_true", help="creates an uri list")
    parser.add_argument(
        "-t",
        "--taggednames",
        required=True,
        help="file path of inflected tagged names (suitable for debug)",
    )
    parser.add_argument("-k", "--kb", required=True, help="knowledgebase file path")
    parser.add_argument(
        "-I", "--indir", help="directory base for auxiliary input files"
    )
    parser.add_argument(
        "-O",
        "--outdir",
        default=".",
        help="directory base cached / temporary / output files",
    )
    parser.add_argument(
        "-c",
        "--clean-cached",
        action="store_true",
        help="do not use previously created cached files",
    )
    parser.add_argument(
        "-n",
        "--processes",
        type=int,
        default=4,
        help="numer of processes for multiprocessing pool.",
    )
    parser.add_argument(
        "-Q",
        "--entity-id",
        action="store_true",
        help="Automata pointer will be entity id (usually wikidata Q-identifier) instead of line number.",
    )
    return parser.parse_args()


def load_kb_struct(lang: str, kb: str):
    # load KB struct
    return metrics_knowledge_base.KnowledgeBase(lang, kb)


def load_namelist_module(lang: str):
    return ModuleLoader.load("namelist", lang, "Namelist", "..dictionaries")


def load_persons_module(lang: str):
    # load laguage specific class of Persons entity
    return EntityLoader.load("persons", lang, "Persons")


""" For firstnames or surnames it creates subnames of each separate name and also all names together """


def get_subnames_from_parts(subname_parts) -> Set[str]:
    subnames = set()
    subname_all = ""
    for subname_part in subname_parts:
        subname_part = regex.sub(
            r"#[A-Za-z0-9]+E?(%s|$)" % RE_NAMES_SEPARATOR, r"\g<1>", subname_part
        )
        subnames.add(subname_part)
        if subname_all:
            subname_part = " " + subname_part
        subname_all += subname_part

    if subname_all:
        subnames.add(subname_all)
    return subnames


def _name_to_upper(name: str) -> str:
    if not name:
       return name
    name_parts = name.split("#")
    name_parts[0] = name_parts[0].upper()
    tmp_name = "#".join(name_parts)

    return tmp_name

def build_name_variant(
    ent_flag,
    strip_nameflags,
    inflection_parts,
    is_basic_form,
    i_inflection_part,
    stacked_name,
    name_inflections,
) -> Tuple[Set[str], Set[str], Set[str]]:
    subnames = set()
    surnames = set()
    separator = ""
    if i_inflection_part < len(inflection_parts):
        for inflected_part in inflection_parts[i_inflection_part]:
            if stacked_name and inflected_part:
                separator = " "
            name_inflections, built_subnames, name_surnames = build_name_variant(
                ent_flag,
                strip_nameflags,
                inflection_parts,
                is_basic_form,
                i_inflection_part + 1,
                stacked_name + separator + inflected_part,
                name_inflections,
            )
            subnames |= built_subnames
            surnames |= name_surnames
    else:
        new_name_inflections = set()
        new_name_inflections.add(stacked_name)

        if ent_flag in ["F", "M"]:
            match_one_firstname_surnames = regex.match(
                r"^([^#]+#j?[G]E?"
                + RE_NAMES_SEPARATOR
                + r")(?:[^#]+#j?[G]E?"
                + RE_NAMES_SEPARATOR
                + r")+((?:[^# "
                + RE_DASHES
                + r"]+#j?SE?(?: \p{L}+#[L78]E?)*(?:"
                + RE_NAMES_SEPARATOR
                + r"|$))+)",
                stacked_name,
            )

            if match_one_firstname_surnames:
                firstname_surnames = match_one_firstname_surnames.group(
                    1
                ) + match_one_firstname_surnames.group(2)
                if firstname_surnames not in name_inflections:
                    new_name_inflections.add(firstname_surnames)

            if is_basic_form:
                firstnames_surnames = regex.match(
                    r"^((?:[^#]+#j?[G]E?"
                    + RE_NAMES_SEPARATOR
                    + r")+)((?:[^# "
                    + RE_DASHES
                    + r"]+#j?SE?(?:"
                    + RE_NAMES_SEPARATOR
                    + r"|$))+)((?:[^# "
                    + RE_DASHES
                    + r"]+#[L78]E?(?:"
                    + RE_NAMES_SEPARATOR
                    + r"|$))*)",
                    stacked_name,
                )
                if firstnames_surnames:
                    name_surnames = firstnames_surnames.group(2).strip()
                    surnames.add(name_surnames)
                    new_name_inflections.add(
                        firstnames_surnames.group(1)
                        + firstnames_surnames.group(2).strip()
                    )  # Tadeáš Hájek z Hájku -> Tadeáš Hájek
                    new_name_inflections.add(
                        firstnames_surnames.group(1)
                        + _name_to_upper(name=firstnames_surnames.group(2)).strip()
                    )  # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK
                    if len(firstnames_surnames.groups()) == 3:
                        new_name_inflections.add(
                            firstnames_surnames.group(1)
                            + _name_to_upper(name=firstnames_surnames.group(2))
                            + firstnames_surnames.group(3)
                        )  # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK z Hájku
                        new_name_inflections.add(
                            firstnames_surnames.group(1)
                            + _name_to_upper(name=firstnames_surnames.group(2))
                            + _name_to_upper(name=firstnames_surnames.group(3)).strip()
                        )  # Tadeáš Hájek z Hájku -> Tadeáš HÁJEK Z HÁJKU
                    # firstnames_surnames = firstnames_surnames.group(1) + firstnames_surnames.group(2).upper()
                    # if firstnames_surnames != stacked_name:
                    # new_name_inflections.add(firstnames_surnames)

            for n in new_name_inflections:
                subnames |= get_subnames_from_parts(regex.findall(r"(\p{L}+#j?GE?)", n))
                subnames |= get_subnames_from_parts(
                    regex.findall(r"(\p{L}+#j?SE?(?: \p{L}+#[L78])*)", n)
                )
            subnames = persons.get_normalized_subnames(subnames)
        if strip_nameflags:
            for n in new_name_inflections:
                name_stripped = regex.sub(
                    r"#[A-Za-z0-9\.]+E?(?=" + RE_DASHES_VARIANTS + r"|,| |\u200b|$)",
                    "",
                    n,
                )
                name_stripped = regex.sub(r"\u200b", "", name_stripped)
                name_inflections.add(name_stripped)
        else:
            name_inflections |= new_name_inflections
    return name_inflections, subnames, surnames


def get_KB_names_ntypes_for(_fields):
    names = dict()
    str_name = kb_struct.get_data_for(_fields, "NAME")
    str_aliases = kb_struct.get_data_for(_fields, "ALIASES")
    str_aliases = regex.sub(r"#lang=[^#|]*", "", str_aliases)

    # Assign redirects also as aliases
    aliases = str_aliases.split(
        KB_MULTIVALUE_DELIM
    )  # + kb_struct.get_data_for(_fields, 'REDIRECTS').split(KB_MULTIVALUE_DELIM)

    names[str_name] = None
    for alias in str_aliases.split(KB_MULTIVALUE_DELIM):
        ntype = regex.search(r"#ntype=([^#|]*)", alias)
        if ntype:
            ntype = ntype.group(1)
        if not ntype:  # unify also for previous
            ntype = None
        k_alias = regex.sub(r"#ntype=[^#|]*", "", alias).strip()
        if k_alias and k_alias not in names:
            names[k_alias] = ntype
    return names


def combine_special_separated_parts(
    special_parts: Dict[int, Set[str]],
    special_separators: Union[str, Dict[int, Set[str]]],
    i_part: int = 0,
    stacked_name: str = "",
) -> Set[str]:
    output = set()
    if i_part < len(special_parts):
        for part in special_parts[i_part]:
            if isinstance(special_separators, str):
                curent_special_separator = special_separators
            else:
                if i_part < len(special_parts) - 1:
                    curent_special_separator = special_separators[i_part]
                else:
                    curent_special_separator = ''
            output |= combine_special_separated_parts(
                special_parts=special_parts,
                special_separators=special_separators,
                i_part=i_part + 1,
                stacked_name=f"{stacked_name}{part}{curent_special_separator}",
            )
        return output
    else:
        if isinstance(special_separators, str):
            stacked_name = stacked_name.rstrip(special_separators)
        return set([stacked_name])


def process_name_inflections(
    line: str, strip_nameflags: bool = True
) -> Tuple[str, Set[str], Set[str], Dict, Set[str]]:
    subnames = set()
    surnames_uris = {}
    surnames = set()
    name_inflections = set()

    name, lang, flags, inflections, uri = _get_values_from_tagged_inflections_line(
        line=line
    )

    for idx, infl in enumerate(inflections):
        inflection_parts = {}
        for i_infl_part, infl_part in enumerate(infl.split(" ")):
            inflection_parts[i_infl_part] = set()

            part_variant_suffix = ""
            # for comma-contained names like ...Sloanu#../Sloanovi#..,...
            if infl_part[-1] == ",":
                part_variant_suffix = infl_part[-1]
                infl_part = infl_part[:-1]

            is_spec_char = False
            spec_char = "\u200b"
            if spec_char in infl_part:
                is_spec_char = True
                zerowidth_parts = {}
                for i_zw_part, infl_zw_part in enumerate(infl_part.split(spec_char)):
                    zerowidth_parts[i_zw_part] = TaggedInflections._separate_part_variants(
                        name_part=infl_zw_part, part_variant_suffix=part_variant_suffix
                    )

                inflection_parts[i_infl_part] |= combine_special_separated_parts(
                    special_parts=zerowidth_parts, special_separators=spec_char
                )

            # for dash-contained names like ...Adamovi#../Adamu#..-Philippovi#../Philippu#...
            # dash variants: 0x2D (0045), 0x96 (0150), 0x97 (0151), 0xAD (0173)
            # regex splitting is needed due to Adamovi#../Adamu#..-Philippovi#../Philippu#.. vs. Bo-gdanovići#../Bo-gdanovićovi#..
            is_dashed = False
            matches = regex.findall(
                r"([^/#]*#[^/"
                + RE_DASHES
                + r"]*(?:/[^#]*#[^/"
                + RE_DASHES
                + r"]*)*)("
                + RE_DASHES_VARIANTS
                + r"|$)",
                infl_part,
            )
            if matches and len(matches) > 1:
                is_dashed = True
                dashed_parts = {}
                parts_separators = {}
                for i_dashed_part, infl_dashed_item in enumerate(matches):
                    dashed_parts[i_dashed_part] = TaggedInflections._separate_part_variants(
                        name_part=infl_dashed_item[0],
                        part_variant_suffix=part_variant_suffix,
                    )
                    parts_separators[i_dashed_part] = infl_dashed_item[1]
                inflection_parts[i_infl_part] |= combine_special_separated_parts(
                    special_parts=dashed_parts, special_separators=parts_separators
                )
            if is_dashed == False and is_spec_char == False:
                inflection_parts[i_infl_part] |= TaggedInflections._separate_part_variants(
                    name_part=infl_part, part_variant_suffix=part_variant_suffix
                )

        built_name_inflections, built_subnames, build_surnames = build_name_variant(
            flags[-1] if len(flags) else "",
            strip_nameflags,
            inflection_parts,
            idx == 0,
            0,
            "",
            set(),
        )

        name_inflections |= built_name_inflections
        subnames |= built_subnames
        if idx == 0:
            surnames_parts = set()
            for surname in build_surnames:
                surnames_parts |= set(
                    regex.split(" |\u200b|" + RE_DASHES_VARIANTS, surname)
                )
            build_surnames |= surnames_parts
            for surname in build_surnames:
                surname = _strip_surname_flags(surname=surname)
                surname = surname.strip(f" ,{DASHES}")
                if surname.lower() == surname:
                    logging.debug(f"Skipping surname \"{surname}\" (of name \"{name}\")..")
                    continue

                surname_key = _get_surname_entity_key(
                    surname=surname, lang=lang, flags=flags
                )
                if surname_key not in surnames_uris:
                    surnames_uris[surname_key] = set()
                surnames_uris[surname_key].add(uri)
                surnames.add(surname)
    if len(inflections) == 0 and len(flags) and flags[-1] in ["F", "M"]:
        subnames |= persons.get_normalized_subnames(
            src_names=[name], separate_to_names=True
        )
    return name, name_inflections, subnames, surnames_uris, surnames


def _get_values_from_tagged_inflections_line(
    line: str
) -> Tuple[str, str, str, List[str], str]:
    divider = "\t"
    line_columns = line.split(divider)
    try:
        name, lang, flags, inflections, uri, _namegen_flags = line_columns
    except ValueError:
        raise ValueError(
            "UNEXPECTED number of columns in namegen output - 6 are expected; {len(line_columns)} was/were given ({line_columns})"
        )
    inflections = inflections.split("|") if inflections != "" else []
    return name, lang, flags, inflections, uri


class TaggedInflections:
    def __init__(
        self,
        lang: str,
        path_entities_taggednames: str,
        namelist: Namelist,
        outdir: str,
        n_processes: int,
    ) -> None:
        self.subnames = set()
        self.named_inflections = {}
        self.surnames_names_map = {}
        self.derivatives_inflections = {}

        self._lang = lang
        self._n_processes = n_processes
        self._namelist = namelist
        self._outdir = outdir
        self._path_entities_taggednames = path_entities_taggednames
        self._path_derivatives_taggednames = path_join(
            self._outdir, "surnames_tagged_inflections.tsv"
        )
        self._surnames_uris = {}

    def load_subnames_and_named_inflections(self, strip_nameflags: bool = True) -> None:
        if not args.clean_cached and are_files_with_content(
            paths=set(
                [
                    self._get_path_cached_subnames(),
                    self._get_path_cached_inflectednames(),
                    self._get_path_surnames_with_typeflags(),
                    self._get_path_surnames_names_map(),
                ]
            )
        ):
            self.subnames = pickle_load(self._get_path_cached_subnames())
            self.named_inflections = pickle_load(self._get_path_cached_inflectednames())
            self.surnames_names_map = json_load(self._get_path_surnames_names_map())
        else:
            self._process_entities_taggednames_results(
                self._process_entities_taggednames(strip_nameflags=strip_nameflags)
            )
            pickle_dump(self.subnames, self._get_path_cached_subnames())
            pickle_dump(self.named_inflections, self._get_path_cached_inflectednames())
            self._dump_surnames_with_typeflags()
            json_dump(self.surnames_names_map, self._get_path_surnames_names_map())
        self._namelist.add_subnames(self.subnames)
        self._namelist.add_alternatives(self.named_inflections)


    def load_derivatives_inflections(self, strip_nameflags: bool = True) -> None:
        for name, inflections in self._process_derivatives_taggednames(strip_nameflags=strip_nameflags):
            for surname_name in self.surnames_names_map[name]:
                DictTools.add_to_dict_key(
                    dictionary=self.derivatives_inflections, key=surname_name, items=inflections
                )
        self._namelist.add_alternatives(self.derivatives_inflections)


    def process_derivatives_inflections(self) -> None:
        infile = self._get_path_surnames_with_typeflags()
        outfile = self._path_derivatives_taggednames
        if (
            not args.clean_cached
            and is_file_with_content(outfile)
            and getmtime(outfile) > getmtime(infile)
        ):
            logging.info(
                f'Using cached namegen output ("{outfile}") for surname derivatives...'
            )
        else:
            logging.info("Running namegen for surnames derivatives...")
            module2import = "lang_modules.{}.entities_tagged_inflections".format(
                self._lang
            )
            try:
                module_eti = importlib.import_module(module2import)
                eti = module_eti.EntitiesTaggedInflections(
                    infile=infile,
                    outfile=outfile,
                    eti_mode=EtiMode.DERIV,
                )
                eti.process()
            except ModuleNotFoundError as e:
                logging.waning(
                    f"Problem in tagged inflections for entities: No implementation for given language. (Detail: {e})"
                )

    def _dump_surnames_with_typeflags(self) -> None:
        if not self._surnames_uris:
            logging.warning(
                f'Can not save "{self._get_surnames_with_typeflags()}" due to empty data.'
            )
        with open(self._get_path_surnames_with_typeflags(), "w") as f:
            for surname_data, uris in self._surnames_uris.items():
                f.write(f"{surname_data}\t{'|'.join(uris)}\n")

    def _get_path_cached_subnames(self) -> str:
        return path_join(self._outdir, "cached_subnames.pkl")

    def _get_path_cached_inflectednames(self) -> str:
        return path_join(self._outdir, "cached_inflectednames.pkl")

    def _get_path_surnames_names_map(self) -> str:
        return path_join(self._outdir, "surnames_names_map.json")

    def _get_path_surnames_with_typeflags(self) -> str:
        return path_join(self._outdir, "surnames_with_typeflags.tsv")

    def _process_common_taggednames(
        self, input: str, processor: Callable, strip_nameflags: bool = True
    ) -> Iterable[Tuple]:
        pool = Pool(self._n_processes)
        try:
            with open(input) as f:
                return pool.starmap(processor, zip(f, repeat(strip_nameflags)))
        except FileNotFoundError:
            pass

    def _derivatives_taggednames_processor(
        self, line: str, strip_nameflags: bool = True
    ) -> Tuple[str, Set[str]]:
        name, lang, flags, _inflections, uri = _get_values_from_tagged_inflections_line(
            line=line
        )
        inflections = set()
        for inflection in _inflections:
            name_parts = regex.split(r"(%s)" % RE_NAMES_SEPARATOR, inflection)
            if len(name_parts) > 1:
                name_parts_names = name_parts[::2]
                name_parts_separators = dict(enumerate(name_parts[1::2]))
                name_parts_names = dict(enumerate([self._separate_part_variants(name_part=x) for x in name_parts_names]))
                combine_special_separated_parts(
                    special_parts=name_parts_names,
                    special_separators=list(name_parts_separators)
                )
            else:
                inflections.update(self._separate_part_variants(name_part=inflection))
        return name, inflections

    def _process_derivatives_taggednames(
        self, strip_nameflags: bool = True
    ) -> Iterable[Tuple]:
        return self._process_common_taggednames(
            input=self._path_derivatives_taggednames,
            processor=self._derivatives_taggednames_processor,
            strip_nameflags=strip_nameflags,
        )

    def _process_entities_taggednames(
        self, strip_nameflags: bool = True
    ) -> Iterable[Tuple]:
        return self._process_common_taggednames(
            input=self._path_entities_taggednames,
            processor=process_name_inflections,
            strip_nameflags=strip_nameflags,
        )

    def _process_entities_taggednames_results(self, results: Iterable[Tuple]) -> None:
        for name, inflections, subnames, surnames_uris, surnames in results:
            DictTools.add_to_dict_key(
                dictionary=self.named_inflections, key=name, items=inflections
            )
            self.subnames |= subnames
            for surname_key, uris in surnames_uris.items():
                DictTools.add_to_dict_key(
                    dictionary=self._surnames_uris, key=surname_key, items=uris
                )
            for surname in surnames:
                if surname in self.surnames_names_map:
                    self.surnames_names_map[surname].add(name)
                else:
                    self.surnames_names_map[surname] = {name}

    @staticmethod
    def _separate_part_variants(name_part: str, part_variant_suffix: str = "") -> Set[str]:
        part_variants = set()
        for part_variant in name_part.split("/"):
            part_variants.add(
                regex.sub(r"(\p{L}*)(\[[^\]]+\])?", r"\g<1>", part_variant)
                + part_variant_suffix
            )
        return part_variants


""" Processes a line with entity of argument determined type. """
def add_line_of_type_to_dictionary(_fields, _line_num, _type_set):
    aliases = get_KB_names_ntypes_for(_fields)
    for alias, ntype in aliases.items():
        transformed_alias = [alias]
        if "event" in _type_set:
            if len(alias) > 1:
                transformed_alias = [
                    alias[0].upper() + alias[1:],
                    alias[0].lower() + alias[1:],
                ]  # capitalize destroys other uppercase letters to lowercase
        elif "organisation" in _type_set:
            transformed_alias = [
                alias,
                " ".join(
                    word[0].upper() + word[1:] if len(word) > 1 else word
                    for word in alias.split()
                ),
            ]  # title also destroys other uppercase letters in word to lowercase

        for ta in transformed_alias:
            add_to_namelist(
                _key=ta,
                _nametype=ntype,
                _value=_line_num,
                _type_set=_type_set,
                _fields=_fields,
            )


def process_person_common(person_type, _fields, _line_num, confidence_threshold):
    """Processes a line with entity of any subtype of person type."""

    aliases = get_KB_names_ntypes_for(_fields)
    name = kb_struct.get_data_for(_fields, "NAME")
    try:
        confidence = float(to_numeric(kb_struct.get_data_for(_fields, "CONFIDENCE")))
    except RuntimeError:
        confidence = None

    processed_surnames = set()
    for n, t in aliases.items():
        add_to_namelist(
            _key=n,
            _nametype=t,
            _value=_line_num,
            _type_set=person_type,
            _fields=_fields,
        )

    if confidence is not None and confidence >= confidence_threshold:
        surname_match = SURNAME_MATCH.search(name)
        unwanted_match = UNWANTED_MATCH.search(name)
        if surname_match and not unwanted_match:
            surname = surname_match.group(0)
            if surname not in processed_surnames and surname != name:
                processed_surnames.add(surname)
                add_to_namelist(
                    _key=surname,
                    _nametype=t,
                    _value=_line_num,
                    _type_set=person_type,
                    _fields=_fields,
                )


def add_to_namelist(
    _key: str, _nametype: str, _value: str, _type_set: Set[str], _fields: List[str]
) -> None:
    namelist.add_variants(
        key=_key,
        nametype=_nametype,
        link=_value,
        type_set=_type_set,
        kb_item_cols=_fields,
    )


def process_other(_fields, _line_num):
    """Processes a line with entity of other type."""

    add_line_of_type_to_dictionary(_fields, _line_num, _fields[1])


def process_uri(_fields, _line_num):
    """Processes all URIs for a given entry."""
    entity_head = kb_struct.get_ent_head(_fields)

    uris = []
    for uri_column_name in URI_COLUMN_NAMES:
        if uri_column_name in entity_head:
            uris.append(kb_struct.get_data_for(_fields, uri_column_name))
    if "OTHER URL" in entity_head:
        uris.extend(
            kb_struct.get_data_for(_fields, "OTHER URL").split(KB_MULTIVALUE_DELIM)
        )
    uris = [u for u in uris if u.strip() != ""]

    for u in uris:
        namelist.add_uri(u, _line_num)


def loadListFromFile(fname: str, use_lang_prefix: bool = True) -> List:
    try:
        with open(
            path_join(args.indir, args.lang, f"{args.lang}_{fname}")
            if use_lang_prefix
            else fname
        ) as fh:
            return fh.read().splitlines()
    except FileNotFoundError:
        print(
            'WARNING: File "{}" was not found => continue with empty list.'.format(
                fname
            ),
            file=stderr,
            flush=True,
        )
        return []


def _strip_surname_flags(surname: str) -> str:
    return regex.sub(r"#j?SE?", "", surname)


def _get_surname_entity_key(surname: str, lang: str, flags: str) -> str:
    return "\t".join([surname, lang, flags])


if __name__ == "__main__":
    args = parse_args()

    if not args.indir or not isdir(args.indir):
        args.indir = path_join(
            dirname(realpath(__file__)), "inputs/{}".format(args.lang)
        )

    # automata variants config
    atm_config = AutomataVariants.DEFAULT
    if args and args.lowercase:
        atm_config |= AutomataVariants.LOWERCASE
    if args and args.autocomplete:
        # different format - can not be combined with other types
        atm_config = AutomataVariants.NONACCENT

    kb_struct = load_kb_struct(lang=args.lang, kb=args.kb)
    namelist = load_namelist_module(lang=args.lang)
    namelist.set_kb_struct(kb_struct)
    namelist.set_automata_variants(atm_config)

    UNWANTED_MATCH = namelist.re_unwanted_match()
    persons = load_persons_module(lang=args.lang)

    if args.uri:
        # processing the KB
        for line_num, fields in enumerate(
            kb_struct.getKBLines(args.kb, metrics_knowledge_base.KB_PART.DATA), start=1
        ):
            process_uri(fields, str(line_num))

    else:
        # loading the list of titles, degrees etc. (earl, sir, king, baron, ...)
        namelist.set_freq_terms(loadListFromFile(fname="freq_terms.lst"))

        # loading the allow list (these names will be definitely in the namelist)
        namelist.set_allowed(loadListFromFile(fname="allow_list.lst"))

        # loading the list of first names
        # lst_firstnames = loadListFromFile("firstnames.lst")

        # loading the list of all nationalities
        # lst_nationalities = loadListFromFile("nationalities.lst")

        # load frequency for words
        logging.info("Loading word frequency...")
        namelist.load_frequency(
            outdir=args.outdir, indir=args.indir, clean_cached=args.clean_cached
        )

        logging.info("Processing namegen for common names...")
        tagged_inflections = TaggedInflections(
            lang=args.lang,
            path_entities_taggednames=args.taggednames,
            namelist=namelist,
            outdir=args.outdir,
            n_processes=args.processes,
        )
        tagged_inflections.load_subnames_and_named_inflections(strip_nameflags=False)
        gc.collect()

        tagged_inflections.process_derivatives_inflections()
        tagged_inflections.load_derivatives_inflections()

        logging.info("Running NER actions...")

        # processing the KB
        for line_num, fields in enumerate(
            kb_struct.getKBLines(args.kb, metrics_knowledge_base.KB_PART.DATA), start=1
        ):
            ent_type_set = kb_struct.get_ent_type(fields)

            if args.entity_id:
                entity_pointer = kb_struct.get_data_for(fields, "ID")
                if entity_pointer[0] == "Q":
                    entity_pointer = entity_pointer[1:]
            else:
                entity_pointer = str(line_num)

            if "person" in ent_type_set:
                confidence_threshold = 20
                if (
                    "artist" in ent_type_set
                    or kb_struct.get_data_for(fields, "FICTIONAL") == "1"
                ):
                    confidence_threshold = 15
                process_person_common(
                    ent_type_set, fields, entity_pointer, confidence_threshold
                )
            else:
                process_other(fields, entity_pointer)
        # gc.collect()

    # printing the output
    namelist.get_tsv(include_extra=True)  # not args.uri)
