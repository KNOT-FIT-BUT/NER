#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import regex
import sys

from abc import ABC, abstractmethod
from os.path import join as path_join
from sys import stdout, stderr
from typing import Dict, List, Optional, Set, TextIO

from automata.src.definitions import DASHES, RE_DASHES_VARIANTS
from automata.src.dict_tools import DictTools
from automata.src.metrics_knowledge_base import KnowledgeBase
from automata.src.word_frequency import (
    FrequencyMeasures,
    WordFrequency,
    WordFrequencyInputNotReadable,
)
from libs.automata_variants import AutomataVariants
from libs.utils import remove_accent
from libs.entities.entity_loader import EntityLoader
from libs.lib_loader import LibLoader
from libs.nationalities.nat_loader import NatLoader


class Namelist(ABC):
    NONACCENT_TYPES = set(["person", "geographical"])

    RE_FLAG_NAMES = r"(?:#j?[A-Z0-9]+E?)"
    RE_FLAG_ONLY1ST_FIRSTNAME = r"(?:#j?[GI]E?)"
    RE_FLAG_FIRSTNAME = r"(?:#j?[G]E?)"
    RE_FLAG_SURE_SURNAME = r"(?:#j?[^GI]E?)"
    RE_FLAGNAME_SEPARATOR = r"(?:\s|\u200b|-)"

    def __init__(self, lang: str) -> None:
        self._lang = lang

        self._ntokb = NatLoader.load(lang)
        self._persons = EntityLoader.load(
            module="persons", lang=lang, initiate="Persons"
        )

        # Regex for all inflections of "Svatý" (or particular language variant)
        self._re_saint = r"({})\s".format(
            "|".join(self._re_escape_set(self._get_saint_variants()))
        )
        self._saint_abb = self._get_saint_abb().strip().rstrip(".")
        escaped_saint_abb = regex.escape(self._saint_abb)
        # Regex for "Sv " for example in "Sv Jan"
        self._re_saint_abb_only = r"{}\s".format(escaped_saint_abb)
        # Regex for "Sv. " for example in "Sv. Jan" or "Sv." in "Sv.Jan"
        self._re_saint_abb_dot = r"{}\.\s?".format(escaped_saint_abb)
        self._re_saint_abbs = r"({}|{})".format(
            self._re_saint_abb_dot, self._re_saint_abb_only
        )  # common regex for both of previous 2

        self._lst_freqterms = []
        self._lst_allowed = []
        self._alternatives = {}
        self._automata_variants = AutomataVariants.DEFAULT
        self._kb_struct = None
        self._word_frequency: Dict[str, FrequencyMeasures] = None
        self._subnames = set()

        self._name_variants = set()

        self._namelist = {}

        self._debug_mode = True
        self._debug_entity = None
        logging.basicConfig(
            format="[%(asctime)s - %(levelname)s]:   %(message)s",
            level=logging.DEBUG if self._debug_mode else logging.WARNING,
        )

    @abstractmethod
    def _get_person_lang_unwanted_start_matches(self) -> Set[str]:
        raise NotImplementedError(
            "Missing implementation of _get_person_lang_unwanted_matches()"
        )

    @abstractmethod
    def _get_saint_variants(self) -> Set[str]:
        raise NotImplementedError("Missing implementation of _get_saint_variants()")

    @abstractmethod
    def _get_saint_abb(self) -> str:
        raise NotImplementedError("Missing implementation of _get_saint_abb()")

    @abstractmethod
    def _get_lang_unwanted_matches(self) -> Set[str]:
        return set()

    def set_allowed(self, lst_allowed: List[str]) -> None:
        self._lst_allowed = lst_allowed

    def add_alternatives(self, alternatives: Dict[str, str]) -> None:
        DictTools.add_to_dict(dictionary=self._alternatives, added_dict=alternatives)

    def set_automata_variants(self, automata_variants: AutomataVariants) -> None:
        self._automata_variants = automata_variants

    def set_freq_terms(self, lst_freqterms: List[str]) -> None:
        self._lst_freqterms = lst_freqterms

    def set_kb_struct(self, kb_struct: KnowledgeBase) -> None:
        self._kb_struct = kb_struct

    def add_subnames(self, subnames: Set[str]) -> None:
        self._subnames = self._subnames | subnames

    def re_unwanted_match(self) -> str:
        unwanted_match = self._re_escape_set(
            self._get_saint_variants()
        ) | self._re_escape_set(self._get_lang_unwanted_matches())
        return regex.compile(
            r"(,|[0-9]|(^|\s)({})(\s|$))".format("|".join(unwanted_match))
        )

    def add_uri(self, key: str, link: str) -> None:
        self._save_key_to_namelist(key=key, link=link)

    def add_variants(
        self,
        key: str,
        nametype: str,
        link: str,
        type_set: Set[str],
        kb_item_cols: List[str],
    ) -> None:
        """
        Adds the name into the dictionary. For each name it adds also an alternative without accent.

        Args:
                key: the name of a given entity
                nametype: type of name given in key parameter
                link: the line number (from the KB) corresponding to a given entity
                type_set: the type of a given entity
                kb_item_cols: all KB columns for entity given in key parameter
        """

        if self._kb_struct is None:
            raise Exception(
                "ERROR: KB Struct was probably not set by setKBStruct() method."
            )

        # remove multiple white spaces
        key = regex.sub(r"\s+", " ", key).strip()

        # there are no changes for the name from the allow list
        if key not in self._lst_allowed and self._is_unsuitable_key(
            key=key, type_set=type_set
        ):
            return

        self._debug_entity = key

        # All following transformatios will be performed for each of inflection
        # variant of key_inflection
        for key_inflection in self._get_key_inflections(
            key=key, nametype=nametype, type_set=type_set
        ):
            # adding name into the dictionary
            self._add(key=key_inflection)

            # adding various alternatives for given types
            if "event" not in type_set:
                self._add_not_event_variants(key=key_inflection)

            if "person" in type_set:
                self._add_person_variants(
                    key=key_inflection,
                    nametype=nametype,
                    link=link,
                    type_set=type_set,
                )

            if "geographical" in type_set:
                self._add_geographical_variants(
                    key=key_inflection,
                    kb_item_cols=kb_item_cols,
                )

            # if 'event' in type_set:
            # if len(regex.findall(r"^[0-9]{4} (Summer|Winter) Olympics$", key_inflection)) != 0:
            # location = self._kb_struct.get_data_for(kb_item_cols, 'LOCATIONS')
            # year = self._kb_struct.get_data_for(kb_item_cols, 'START DATE')[:4]
            # if year and location and "|" not in location:
            # self._add("Olympics in " + location + " in " + year) # 1928 Summer Olympics -> Olympics in Amsterdam in 1928
            # self._add("Olympics in " + year + " in " + location) # 1928 Summer Olympics -> Olympics in 1928 in Amsterdam
            # self._add("Olympic Games in " + location + " in " + year) # 1928 Summer Olympics -> Olympic Games in Amsterdam in 1928
            # self._add("Olympic Games in " + year + " in " + location) # 1928
            # Summer Olympics -> Olympic Games in 1928 in Amsterdam

        self._do_conversions_for_i_with_grave()
        if "person" in type_set:
            self._do_conversions_for_persons_names()

        self._save_name_variants_to_namelist(link=link, type_set=type_set)

    def get_tsv(
        self,
        include_extra: bool = False,
        sort_links: bool = False,
        outfile: TextIO = stdout,
    ) -> None:
        """
        Generate namelist and print it to given output file (stdout as default).

        Args:
                include_extra: Adds some specific items to namelist (for example all subnames will be marked with "N")
                sort_links: Sort links otherwise they have random order due to set.
        """
        for key, links in self._generate_namelist_dict(include_extra).items():
            if sort_links:
                include_n = False
                if "N" in links:
                    include_n = True
                    links.remove("N")
                links = sorted(links, key=int)
                if include_n:
                    links.append("N")
            print(key + "\t" + ";".join(links), file=outfile)

    def is_capital_dominant(self, name: str) -> bool:
        if not isinstance(name, str):
            raise TypeError(
                f'Type conflict - expected "str"; got "{type(name).__name__}".'
            )
        if name[0].title() != name[0]:
            return False
        if name.title() != name:
            return True
        if name.lower() not in self._word_frequency:
            return True
        return name in self._word_frequency and self._word_frequency[name].uplow >= 0.5

    def load_frequency(
        self, outdir: str, indir: str, clean_cached: bool = False
    ) -> None:
        freq_file = path_join(indir, self._lang, f"{self._lang}_CWC.wc")
        try:
            wf = WordFrequency(filepath=freq_file)
            self._word_frequency = wf.load_frequency(
                outfile=path_join(outdir, "word_frequency.json"),
                clean_cached=clean_cached,
            )
        except WordFrequencyInputNotReadable:
            print(
                f'WARNING: Word frequence file "{freq_file}" was not found => ignoring word frequency.',
                file=stderr,
            )

    def _add(self, key: str) -> None:
        """
        Adds the name into the namelist.

        Args:
                key: the name
        """

        self._name_variants.add(key)
        if "\u200b" in key:
            # Add new key with space instead of zero width space (including
            # insurance against presence of multiple space due to added new
            # one)
            self._name_variants.add(regex.sub(r"\u200b *", " ", key))

    def _remove_flags(self, name: str) -> str:
        name = regex.sub(
            r"#[A-Za-z0-9]+E?(?=\u200b| |,|\.|-|–|$)", "", name
        )  # \u200b = zero width space
        name = regex.sub(r"\u200b", "", name)

        return name.strip()

    def _save_name_variants_to_namelist(self, link: str, type_set: Set[str]) -> None:
        """
        Save all variants of name to namelist dictionary.

        It also removes all name tags from namegen and save particular particular form of the name depending on selected automata variant.

        Args:
                link: Link to KnowledgeBase row for these name variants.
                type_set: Set of types, to which these name variants belong.
        """

        for name_variant in self._name_variants:
            # temporary fix for mountains like K#L12, K#L2, ... (will be solved
            # by extra separator by M. Dočekal)
            key = regex.sub(r"#L(?=[0-9])", "", name_variant)
            # temporary fix for ordinals like <something> 1.#4díl, ... (will be
            # solved by extra separator by M. Dočekal)
            key = regex.sub(r"(?<=\.)#4", "", key)

            preferred_name = False
            n_parts = key.count("#")
            if n_parts == 1:
                if regex.search(r"#j?[LS]E?", key):
                    preferred_name = True
            elif n_parts == 0:
                n_parts = key.count(" ") + 1

            key_with_flags = key
            key = self._remove_flags(name=key)
            key = self._get_key_by_atm_variant(key=key)

            if n_parts == 1:
                is_capital_dominant = self.is_capital_dominant(name=key)
                if not (preferred_name or is_capital_dominant):
                    logging.debug(
                        f'Skipping name "{key}" (original with flags = "{key_with_flags}"; is preferred = {preferred_name}; is_capital_dominant = {is_capital_dominant})'
                    )
                    continue

            # removing entities that begin with '-. or space
            if len(regex.findall(r"^[ '-\.]", key)) != 0:
                continue

            # adding the type-specific prefix to begining of the name
            if AutomataVariants.NONACCENT & self._automata_variants:
                valid_type = False
                for nonacc_type in self.NONACCENT_TYPES:
                    if nonacc_type in type_set:
                        valid_type = True
                        # adding the name into the dictionary
                        self._save_key_to_namelist(
                            key=self._get_non_accent_key(key, nonacc_type), link=link
                        )

                if not valid_type:
                    self._save_key_to_namelist(
                        key=self._get_non_accent_key(key, "other"), link=link
                    )
            else:
                self._save_key_to_namelist(key=key, link=link)
        self._name_variants.clear()

    def _add_geographical_variants(self, key: str, kb_item_cols: List[str]) -> None:
        description = self._kb_struct.get_data_for(kb_item_cols, "DESCRIPTION")
        if key in description:
            country = self._kb_struct.get_data_for(kb_item_cols, "COUNTRY")
            if country and country not in key:
                self._add(key + ", " + country)  # Peking -> Peking, China
                self._add(regex.sub("United States", "US", key + ", " + country))

    def _add_not_event_variants(self, key: str) -> None:
        if (
            regex.search(self._re_saint, key) is not None
            or regex.search(self._re_saint_abbs, key) is not None
        ):
            saint_abb_name = regex.sub(
                r"({}|{})".format(self._re_saint, self._re_saint_abbs),
                "{}. ".format(self._saint_abb),
                key,
            )  # Svatý Jan / Sv.Jan / Sv Jan -> Sv. Jan
            self._add(saint_abb_name)
            re_saint_pattern = r"(?<=(^|\s)){}(?=\p{{Lu}})"
            self._add(
                regex.sub(
                    re_saint_pattern.format(self._re_saint_abb_dot),
                    "{}.".format(self._saint_abb),
                    saint_abb_name,
                )
            )  # Sv. Jan -> Sv.Jan (Svatý Jan / Sv. Jan / Sv Jan -> Sv.Jan)
            self._add(
                regex.sub(
                    re_saint_pattern.format(self._re_saint_abb_dot),
                    "{} ".format(self._saint_abb),
                    saint_abb_name,
                )
            )  # Sv. Jan -> Sv Jan (Svatý Jan / Sv. Jan / Sv.Jan -> Sv Jan)
            # TODO: If original name is abbreviated - how can we get full name
            # in correct inflected form?
            for saint_variant in self._get_saint_variants():
                # Sv. Jan / Sv.Jan / Sv Jan -> Svatý Jan / Svatá Jan / Svaté
                # Jan / ...
                self._add(
                    regex.sub(
                        re_saint_pattern.format(self._re_saint_abbs),
                        "{} ".format(saint_variant),
                        key,
                    )
                )

    def _debug_msg_name_variants(
        self, original_name_variants: Set[str], name_detail: Optional[str] = None
    ) -> None:
        diff_name_variants = self._name_variants.difference(original_name_variants)
        debug_entity_detail = f" ({name_detail})" if name_detail else ""
        logging.debug(
            f'Name variants for "{self._debug_entity}"{debug_entity_detail} after {sys._getframe(1).f_code.co_name}(): {diff_name_variants} [+{len(diff_name_variants)}]'
        )

    def _do_conversions_for_i_with_grave(self) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        for name in self._name_variants.copy():
            with_grave = False
            if "ì" in name:
                with_grave = True
                # Melozzo da Forlì -> Melozzo da Forlí
                name = regex.sub("ì", "í", name)
            if "Ì" in name:
                with_grave = True
                name = regex.sub("Ì", "Í", name)  # FORLÌ -> FORLÍ
            if with_grave:
                self._add(name)
        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _do_conversions_for_persons_names(self) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        self._do_conversions_for_persons_dashed_names()
        self._do_conversions_for_persons_dotted_names()
        self._do_conversions_for_persons_mc_names()
        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _do_conversions_for_persons_dashed_names(self) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        for name in self._name_variants.copy():
            for dash_type in DASHES:
                if dash_type in name:
                    name_capitalized_parts = []
                    dashed_parts = name.split(dash_type)
                    for i_part, dashed_part in enumerate(dashed_parts):
                        name_capitalized_parts.append(
                            " ".join(
                                [
                                    (dashed_part_name[0].upper() + dashed_part_name[1:])
                                    if len(dashed_part_name) >= 2
                                    else dashed_part_name
                                    for dashed_part_name in dashed_part.split(" ")
                                ]
                            )
                        )
                    # Mao Ce<dash_type>tung -> Mao Ce<dash_type>Tung
                    self._add(dash_type.join(name_capitalized_parts))
                    if dash_type != "-":  # 0x2D (0045)
                        # Mao Ce<dash_type>tung -> Mao Ce-Tung
                        self._add("-".join(name_capitalized_parts))
        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _do_conversions_for_persons_dotted_names(self) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        for name in self._name_variants.copy():
            if "." not in name:
                continue
            # J. M. W. Turner -> J.M.W.Turner
            # Turner, J. M. W. -> Turner, J.M.W.
            name_adjusted = regex.sub(
                r"(\p{Lu}\.%s?) (?=\p{Lu})" % self.RE_FLAG_NAMES, r"\g<1>\u200b", name
            )
            self._add(name_adjusted)

            # J.M.W.Turner -> J.M.W. Turner
            name_adjusted = regex.sub(
                r"(?<!, ?)(\p{Lu}\.%s?)\u200b(?=\p{Lu}\p{L}+)" % self.RE_FLAG_NAMES,
                r"\g<1> ",
                name_adjusted,
            )
            self._add(name_adjusted)

            # Turner, J.M.W -> Turner,J.M.W
            # name_adjusted = regex.sub(
            #    r"(?<=,) (\p{Lu}\.)", r"\g<1>", name_adjusted
            # )
            # self._add(name_adjusted)

            # J.M.W. Turner -> JMW Turner
            # Turner,J.M.W -> Turner,JMW
            # name_adjusted = regex.sub(
            #    r"\.(%s?\u200b?)" % self.RE_FLAG_NAMES, r"\g<1>", name_adjusted
            # )
            # self._add(name_adjusted)

            # Turner,JMW -> Turner, JMW
            # name_adjusted = regex.sub(
            #    r"(?<=,)(\p{Lu})", r" \g<1>", name_adjusted
            # )
            # self._add(name_adjusted)

        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _do_conversions_for_persons_mc_names(self) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        for name in self._name_variants.copy():
            if "Mc" in name:
                self._add(
                    regex.sub(r"Mc(\p{Lu})", r"Mc \g<1>", name)
                )  # McCollum -> Mc Collum
                self._add(
                    regex.sub(r"Mc(?:#[A-Za-z0-9]+)? (\p{Lu})", r"Mc\g<1>", name)
                )  # Mc Collum -> McCollum
        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _add_person_variants(
        self, key: str, nametype: str, link: str, type_set: Set[str]
    ) -> None:
        if nametype != "nick":
            if regex.search(r"#", key):
                self._add_tagged_person_alternatives_variants(key=key)
            else:
                self._add_untagged_person_variants(key=key)

        parts = key.split(" ")
        # if a name contains any of these words, we will not create following
        # adjusments
        if not (set(parts) & set(["von", "van"])):
            for x in self._lst_freqterms:
                if x in key:
                    # John Brown, Jr. -> John Brown
                    new_key = regex.sub(" ?, ?" + x + "$", "", key)
                    # Sir Patrick Stewart -> Patrick Stewart
                    new_key = regex.sub("^" + x + " ", "", new_key)
                    if new_key.count(" ") >= 1:
                        self._add(new_key)

    def _add_tagged_person_alternatives_variants(self, key: str) -> None:
        nameparts = self._get_tagged_person_nameparts(key=key)

        if nameparts == {} or nameparts["sn_last_flags"] not in [
            "#GS",
            "#S",
            "#SE",
            "#jS",
            "#jSE",
            "#R",
        ]:
            logging.debug(
                f'Early termination of _add_tagged_person_alternatives_variants() for "{key}" (nameparts: {nameparts})'
            )
            return

        for i in range(len(nameparts["n_unknowns"]) + 1):
            sep_special = ""
            fn_possible_others_full = ""
            fn_possible_others_abbr = ""

            fn_possible_others = nameparts["fn_others"] + nameparts["n_unknowns"][:i]
            if len(fn_possible_others):
                sep_special = " "
                fn_possible_others_full += " ".join(fn_possible_others)
                for fn_possible_other in fn_possible_others:
                    fn_possible_other_parts = fn_possible_other.split("#")
                    fn_possible_others_abbr += (
                        fn_possible_other[0]
                        + "."
                        + (
                            "#" + fn_possible_other_parts[-1]
                            if len(fn_possible_other_parts) > 1
                            else ""
                        )
                        + " "
                    )
                fn_possible_others_abbr = fn_possible_others_abbr.strip()

            sn_unknowns = " ".join(nameparts["n_unknowns"][i:])
            if sn_unknowns:
                sn_unknowns += " "
            sn_full = nameparts["sn_full"]

            sn_full_alternatives = {sn_full}

            for sn_full_alternative in sn_full_alternatives.copy():
                sn_full_alternatives.update(
                    {
                        sn_unknowns + sn_full_alternative,
                        sn_unknowns + nameparts["n_partonyms"] + sn_full_alternative,
                    }
                )

            for sn_full in sn_full_alternatives:
                self._add_tagged_person_variants(
                    fn_1st=nameparts["fn_1st"],
                    fn_others_full=fn_possible_others_full,
                    fn_others_abbr=fn_possible_others_abbr,
                    sep_special=sep_special,
                    sn_full=sn_full,
                )

    def _add_tagged_person_variants(
        self,
        fn_1st: str,
        fn_others_full: str,
        fn_others_abbr: str,
        sep_special: str,
        sn_full: str,
    ) -> None:
        flags_fn_1st = fn_1st.split("#")
        fn_1st_abbr = (
            f"{fn_1st[0]}.{('#' + flags_fn_1st[-1]) if len(flags_fn_1st) > 1 else ''}"
        )

        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        surname_tags = regex.findall(r"#j?([A-Z])", sn_full)
        # For all of following format exaplaining comments of additions let us
        # assume, that Johann Gottfried Bernhard is firstnames and a surname is
        # Bach only.
        self._add(
            "{} {}{}{}".format(fn_1st, fn_others_abbr, sep_special, sn_full)
        )  # Johann G. B. Bach
        self._add(
            "{} {}{}{}".format(fn_1st_abbr, fn_others_abbr, sep_special, sn_full)
        )  # J. G. B. Bach
        # Johann Bach
        self._add("{} {}".format(fn_1st, sn_full))
        # J. Bach
        self._add("{} {}".format(fn_1st_abbr, sn_full))
        if "R" not in surname_tags:
            self._add(
                "{}, {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_full)
            )  # Bach, Johann Gottfried Bernhard
            # Bach, Johann G. B.
            self._add("{}, {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_abbr))
            # Bach, J. G. B.
            self._add(
                "{}, {}{}{}".format(sn_full, fn_1st_abbr, sep_special, fn_others_abbr)
            )
            # Bach, Johann
            self._add("{}, {}".format(sn_full, fn_1st))
            # Bach, J.
            self._add("{}, {}".format(sn_full, fn_1st_abbr))
            # Bach Johann
            # self._add("{} {}".format(sn_full, fn_1st))
            # Bach Johann Gottfried Bernhard
            self._add("{} {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_full))
            # Bach Johann G. B.
            self._add("{} {}{}{}".format(sn_full, fn_1st, sep_special, fn_others_abbr))
        # Karel I. Veliký -> Karel I.
        surname_parts = regex.search(
            r"%s*(?P<number>[IVXLCDM]+\.#R)%s*(?P<m_name>(?:\p{Lu}')?\p{Lu}\p{L}+#j?ME?$)"
            % (self.RE_FLAGNAME_SEPARATOR, self.RE_FLAGNAME_SEPARATOR),
            sn_full,
        )
        if surname_parts:
            number = surname_parts.group("number")
            self._add(f"{fn_1st} {number}")
        # Bach
        surnames = regex.findall(
            r"(?<=^|%s)(?P<namewithflag>(?P<name>(?:\p{Lu}')?\p{Lu}\p{L}+)(?P<flag>#j?SE?))"
            % self.RE_FLAGNAME_SEPARATOR,
            sn_full,
        )
        for surname_tuple in surnames:
            surname_with_flags = surname_tuple[0]
            surname_without_flags = surname_tuple[1]
            if self.is_capital_dominant(name=surname_without_flags):
                self._add(surname_with_flags)
            else:
                logging.debug(
                    f"Skipped surname: {surname_with_flags} (frequency: {self._get_debug_frequency_info(name=surname_without_flags)})"
                )
        # Ernest T. Seton
        if len(surnames) > 1:
            abbr_surnames = f"{surnames[0][1][0]}.{surnames[0][2]}"
            full_surnames = " ".join(x[0] for x in surnames[1:])
            self._add(
                "{} {}{}{} {}".format(
                    fn_1st, fn_others_full, sep_special, abbr_surnames, full_surnames
                )
            )
            self._add(
                "{} {}{}{} {}".format(
                    fn_1st_abbr,
                    fn_others_abbr,
                    sep_special,
                    abbr_surnames,
                    full_surnames,
                )
            )
            if len(surnames) > 2:
                abbr_surnames = " ".join(f"{x[1][0]}.{x[2]}" for x in surnames[:-1])
                full_surnames = surnames[-1][0]
                self._add(
                    "{} {}{}{} {}".format(
                        fn_1st,
                        fn_others_full,
                        sep_special,
                        abbr_surnames,
                        full_surnames,
                    )
                )
                self._add(
                    "{} {}{}{} {}".format(
                        fn_1st_abbr,
                        fn_others_abbr,
                        sep_special,
                        abbr_surnames,
                        full_surnames,
                    )
                )

        if self._debug_mode:
            self._debug_msg_name_variants(
                original_name_variants=tmp_name_variants,
                name_detail=f'surname variant="{sn_full}"',
            )

    def _add_untagged_person_variants(self, key: str) -> None:
        if self._debug_mode:
            tmp_name_variants = self._name_variants.copy()
        self._add(
            regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", r"\g<1>. \g<2>", key)
        )  # Adolf Born -> A. Born
        self._add(
            regex.sub(
                r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                r"\g<1>. \g<2>. \g<3>",
                key,
            )
        )  # Peter Paul Rubens -> P. P. Rubens
        self._add(
            regex.sub(
                r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                r"\g<1> \g<2>. \g<3>",
                key,
            )
        )  # Peter Paul Rubens -> Peter P. Rubens
        self._add(
            regex.sub(
                r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", r"\g<1> \g<3>", key
            )
        )  # Peter Paul Rubens -> Peter Rubens
        self._add(
            regex.sub(
                r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                r"\g<1>. \g<2>. \g<3>. \g<4>",
                key,
            )
        )  # Johann Gottfried Bernhard Bach -> J. G. B. Bach
        self._add(
            regex.sub(
                r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$",
                r"\g<1>. \g<2>. \g<3> \g<4>",
                key,
            )
        )  # Johann Gottfried Bernhard Bach -> J. G. Bernhard Bach
        self._add(
            regex.sub(
                r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                r"\g<1> \g<2>. \g<3>. \g<4>",
                key,
            )
        )  # Johann Gottfried Bernhard Bach -> Johann G. B. Bach
        self._add(
            regex.sub(
                r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$",
                r"\g<1> \g<2>. \g<3> \g<4>",
                key,
            )
        )  # Johann Gottfried Bernhard Bach -> Johann G. Bernhard Bach
        self._add(
            regex.sub(
                r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                r"\g<1> \g<2> \g<3>. \g<4>",
                key,
            )
        )  # Johann Gottfried Bernhard Bach -> Johann Gottfried B. Bach
        # do not consider "Karel IV." or "Albert II. Monacký", ...
        if not regex.search("[IVX]\\.", key):
            self._add(
                regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", r"\g<2>, \g<1>", key)
            )  # Adolf Born -> Born, Adolf
            # Adolf Born -> Born, A.
            self._add(
                regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", r"\g<2>, \g<1>.", key)
            )
            self._add(
                regex.sub(
                    r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$",
                    r"\g<3>, \g<1> \g<2>",
                    key,
                )
            )  # Johann Joachim Quantz -> Quantz, Johann Joachim
            # Johann Joachim Quantz -> Quantz, J. J.
            self._add(
                regex.sub(
                    r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$",
                    r"\g<3>, \g<1>. \g<2>.",
                    key,
                )
            )
            self._add(
                regex.sub(
                    r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$",
                    r"\g<2> \g<3>, \g<1>",
                    key,
                )
            )  # Tomáš Garrigue Masaryk -> Garrigue Masaryk, Tomáš
            # Tomáš Garrigue Masaryk -> Garrigue Masaryk, T.
            self._add(
                regex.sub(
                    r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$",
                    r"\g<2> \g<3>, \g<1>.",
                    key,
                )
            )
        if self._debug_mode:
            self._debug_msg_name_variants(original_name_variants=tmp_name_variants)

    def _save_key_to_namelist(self, key: str, link: str) -> None:
        if key not in self._namelist:
            self._namelist[key] = set()
        self._namelist[key].add(link)

    def _generate_namelist_dict(self, include_extra: bool = False) -> Dict:
        """
        Generate namelist and return it as a dictionary.

        Args:
                include_extra: Adds some specific items to namelist (for example all subnames will be marked with "N")
        """
        if include_extra:
            # Subnames in all variants with 'N'
            for subname in self._subnames:
                self._save_key_to_namelist(
                    self._get_key_by_atm_variant(key=subname), "N"
                )

            """
			# Pronouns with first lower and first upper with 'N'
			word_types = LibLoader.load('word_types', self._lang, 'WordTypes')
			pronouns = list(word_types.PRONOUNS.keys())
			if not (AutomataVariants.LOWERCASE & self._automata_variants):
				pronouns += [pronoun.capitalize() for pronoun in pronouns]
			if AutomataVariants.NONACCENT & self._automata_variants:
				pronouns += [remove_accent(pronoun) for pronoun in pronouns]
			self._namelist.update(dict.fromkeys(pronouns, 'N'))

			# geting jurisdictions
			jurisdictions = self._ntokb.get_jurisdictions()
			for jur in jurisdictions:
				self._save_key_to_namelist(jur, 'N')
			"""

        return self._namelist

    def _get_debug_frequency_info(self, name: str) -> str:
        if name.title() in self._word_frequency:
            freq = self._word_frequency[name.title()].uplow
        elif name.lower() in self._word_frequency:
            freq = f"available only for lowercases => calculated: {1 - self._word_frequency[name.lower()].uplow}"
        else:
            freq = "NA even for lowercases (=> it should be added automatically)"
        return freq

    def _get_key_by_atm_variant(self, key: str) -> str:
        if AutomataVariants.NONACCENT & self._automata_variants:
            key = remove_accent(key.lower())

        if AutomataVariants.LOWERCASE & self._automata_variants:
            key = key.lower()

        return key

    def _get_key_inflections(self, key: str, nametype: str, type_set: Set[str]) -> Dict:
        key_inflections = None

        if key in self._alternatives:
            key_inflections = self._alternatives[key]
        if not key_inflections:
            # TODO alternative names are not in subnames
            key_inflections = set([key])
            if "person" in type_set and nametype != "nick":
                self._subnames |= self._persons.get_normalized_subnames(
                    set([key]), separate_to_names=True
                )

        for tmp in key_inflections.copy():
            if regex.search(r"%s\p{Lu}" % RE_DASHES_VARIANTS, tmp):
                tmp = regex.sub(r"%s(\p{Lu})" % RE_DASHES_VARIANTS, r" \g<1>", tmp)
                # Payne-John Christo -> Payne John Christo
                key_inflections.add(
                    regex.sub(r"%s(\p{Lu})" % RE_DASHES_VARIANTS, r" \g<1>", tmp)
                )

        return key_inflections

    def _get_non_accent_key(self, key: str, nonacc_type: str) -> str:
        return nonacc_type + ":\t" + key

    def _get_tagged_person_nameparts(self, key: str) -> Dict:
        nameparts = {}
        #      ( <firstname>                           ) ( <other firstnames>                                           )( <partonyms>                         )( <unknowns>                           )( <surnames>                   )
        parts = regex.search(
            r"^(?P<firstname>(?:\p{Lu}')?\p{Lu}\p{L}+%s) (?P<others>(?:(?:(?:\p{Lu}')?\p{L}+#I )*(?:\p{Lu}')?\p{L}+%s )*)(?P<partonyms>(?:\p{Lu}\p{L}+#j[PQ] )*)(?P<unknowns>(?:(?:\p{Lu}')?\p{L}+#I )*)(?P<surnames>(?:\p{Lu}')?(\p{Lu}\p{L}+|[IVXLCDM]+\.)(?<surname_flags>%s).*)$"
            % (
                self.RE_FLAG_ONLY1ST_FIRSTNAME,
                self.RE_FLAG_FIRSTNAME,
                self.RE_FLAG_SURE_SURNAME,
            ),
            key,
        )
        if parts:
            nameparts = {
                "fn_1st": parts.group("firstname"),
                "fn_others": parts.group("others").strip().split(),
                "n_unknowns": parts.group("unknowns").strip().split(),
                "n_partonyms": parts.group("partonyms"),
                "sn_full": parts.group("surnames"),
                "sn_last_flags": parts.group("surname_flags"),
            }
        return nameparts

    def _is_unsuitable_key(self, key: str, type_set: Set[str]) -> bool:
        # we don't want names with any of these characters
        unsuitable = ';?!()[]{}<>/~@#$%^&*_=+|"\\'
        for x in unsuitable:
            if x in key:
                return True

        # inspecting names with numbers
        if len(regex.findall(r"[0-9]+", key)) != 0:
            # we don't want entities containing only numbers
            if len(regex.findall(r"^[0-9 ]+$", key)) != 0:
                return True
            # exception for people or artist name (e.g. John Spencer, 1st Earl
            # Spencer)
            if "person" in type_set:
                if len(regex.findall(r"[0-9]+(st|nd|rd|th)", key)) == 0:
                    return True
            # we don't want locations with numbers at all
            elif "geographical" in type_set:
                return True

        # special filtering for people and artists
        if "person" in type_set:
            # we don't want names starting with some pattern
            # (language specific; for example: "List of ", "Seznam ", ..)
            for unwanted in self._get_person_lang_unwanted_start_matches():
                if key.startswith(unwanted):
                    return True

        # generally, we don't want names starting with low characters (event is
        # needed with low character, ie. "bitva u Waterloo")
        if "event" not in type_set:
            if len(regex.findall(r"^\p{Ll}+", key)) != 0:
                return True

        # filtering out all names with length smaller than 2 and greater than
        # 80 characters
        if len(key) < 2 or len(key) > 80:
            return True

        return False

    def _re_escape_set(self, set2escape: Set[str]) -> Set:
        return set([regex.escape(x) for x in set2escape])
