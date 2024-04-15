from typing import Set
from unittest import TestCase

from automata.src.lang_modules.cs.namelist import Namelist
from automata.src.word_frequency import FrequencyMeasures


class TestNamelist(TestCase):
    def test_do_conversions_for_persons_dotted_names_aanti_full(self) -> None:
        starting_variants = set(
            [
                "Antti#jG Amatus#jGE Aarne#jS",
                "Aarne#jS, Antti#jG Amatus#jGE",
            ]
        )
        namelist = self._get_namelist(starting_name_variants=starting_variants)
        namelist._do_conversions_for_persons_dotted_names()

        self.assertCountEqual(starting_variants, namelist._name_variants)

    def test_is_capital_dominant(self) -> None:
        namelist = self._get_namelist()
        namelist._word_frequency = {
            "lowergtupper": FrequencyMeasures(None, 0.51),
            "Lowergtupper": FrequencyMeasures(None, 0.49),
            "uplowequal": FrequencyMeasures(None, 0.5),
            "Uplowequal": FrequencyMeasures(None, 0.5),
            "uppergtlower": FrequencyMeasures(None, 0.49),
            "Uppergtlower": FrequencyMeasures(None, 0.51),
            "loweronly": FrequencyMeasures(None, 0.5),
            "Upperonly": FrequencyMeasures(None, 0.5),
        }
        for value in [
            "uplowequal",
            "Uplowequal",
            "uppergtlower",
            "Uppergtlower",
            "Upperonly",
            "notexistingkeyinwcmedia",
        ]:
            try:
                self.assertEqual(True, namelist.is_capital_dominant(name=value))
            except AssertionError as e:
                raise AssertionError(f'{e} (for value = "{value}")')
        for value in [
            "lowergtupper",
            "Lowergtupper",
            "loweronly",
        ]:
            try:
                self.assertEqual(False, namelist.is_capital_dominant(name=value))
            except AssertionError as e:
                raise AssertionError(f'{e} (for value = "{value}")')

        for value in [None, 5]:
            self.assertRaises(
                TypeError,
                namelist.is_capital_dominant,
                value,
            )

    def _test_do_conversions_for_persons_dotted_names_aanti_abbr(self) -> None:
        starting_variants = set(
            [
                "A.#jG A.#jGE Aarne#jS",
                "A.#jG Amatus#jGE Aarne#jS",
                "Aarne#jS, A.#jG A.#jGE",
                "Aarne#jS, A.#jG Amatus#jGE",
            ]
        )
        namelist = self._get_namelist(starting_name_variants=starting_variants.copy())
        namelist._do_conversions_for_persons_dotted_names()
        expected_variants = starting_variants | set(
            [
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
            ]
        )

        self.assertCountEqual(expected_variants, namelist._name_variants)

    def _get_namelist(
        self, starting_name_variants: Set = set(), debug_mode: bool = False
    ) -> Namelist:
        namelist = Namelist(lang="cs")
        namelist._debug_mode = debug_mode
        namelist._name_variants = starting_name_variants

        return namelist
