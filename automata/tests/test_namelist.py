import unittest

from typing import Set, Sequence
from unittest.mock import MagicMock, patch

from automata.src.lang_modules.cs.namelist import Namelist

class TestNamelist(unittest.TestCase):
    def test_do_conversions_for_persons_dotted_names_aanti_full(self) -> None:
        starting_variants = set([
            "Antti#jG Amatus#jGE Aarne#jS",
            "Aarne#jS, Antti#jG Amatus#jGE",
        ])
        namelist = self._get_namelist(
            starting_name_variants=starting_variants
        )
        namelist._do_conversions_for_persons_dotted_names()

        self.assertCountEqual(starting_variants, namelist._name_variants)


    def _test_do_conversions_for_persons_dotted_names_aanti_abbr(self) -> None:
        self.maxDiff = None

        starting_variants = set([
            "A.#jG A.#jGE Aarne#jS",
            "A.#jG Amatus#jGE Aarne#jS",
            "Aarne#jS, A.#jG A.#jGE",
            "Aarne#jS, A.#jG Amatus#jGE",
        ])
        namelist = self._get_namelist(
            starting_name_variants=starting_variants.copy()
        )
        namelist._do_conversions_for_persons_dotted_names()
        expected_variants = starting_variants | set([
            "A.#jG\u200bA.#jGE\u200bAarne#jS",
            "A.#jG\u200bA.#jGE Aarne#jS",
            "A#jG\u200bA#jGE Aarne#jS",
            "A#jG A#jGE Aarne#jS",

            "A.#jG\u200bAmatus#jGE Aarne#jS",
            "A#jG Amatus#jGE Aarne#jS",

            "Aarne#jS,A.#jG\u200bA.#jGE",
            "Aarne#jS,A.#jG A.#jGE",
            "Aarne#jS,A#jG\u200bA#jGE",
            "Aarne#jS,A#jG A#jGE",
            "Aarne#jS, A.#jG\u200bA.#jGE",
            "Aarne#jS, A#jG\u200bA#jGE",
            "Aarne#jS, A#jG A#jGE",

            "Aarne#jS,A.#jG\u200bAmatus#jGE",
            "Aarne#jS,A.#jG Amatus#jGE",
            "Aarne#jS,A#jG\u200bAmatus#jGE",
            "Aarne#jS,A#jG Amatus#jGE",
            "Aarne#jS, A.#jG\u200bAmatus#jGE",
            "Aarne#jS, A#jG\u200bAmatus#jGE",
            "Aarne#jS, A#jG Amatus#jGE",
        ])

        self.assertCountEqual(expected_variants, namelist._name_variants)


    def _get_namelist(
        self,
        starting_name_variants: Set,
        debug_mode: bool = False
    ) -> Namelist:
        namelist = Namelist(lang="cs")
        namelist._debug_mode = False
        namelist._name_variants = starting_name_variants

        return namelist
