import unittest

from typing import Set
from unittest.mock import MagicMock

from src import KB2namelist, metrics_knowledge_base

class TestKB2namelist(unittest.TestCase):
    PRINT_DEBUG: bool = True

    def setUp(self) -> None:
        KB2namelist.persons = KB2namelist.load_persons_module("cs")


    def test_dash_delimiter_0x2D_0045(self) -> None:
        return self._test_name_inflections_dash_delimiter(dash_delimiter="-")


    def test_dash_delimiter_0x96_0150(self) -> None:
        return self._test_name_inflections_dash_delimiter(dash_delimiter="–")


    def test_dash_delimiter_0x97_0151(self) -> None:
        return self._test_name_inflections_dash_delimiter(dash_delimiter="—")


    def test_dash_delimiter_0xAD_0173(self) -> None:
        return self._test_name_inflections_dash_delimiter(dash_delimiter="­")


    def test_name_inflections_comma_delimiter(self) -> None:
        expected_basename = "Alfred Pritchard Sloan, Jr."

        firstname_variants = ["Alfredu", "Alfredovi"]
        firstname2nd_variants = ["Pritchardu", "Pritchardovi"]
        surname_variants = ["Sloanu", "Sloanovi"]
        generation_mark = "Jr."

        expected_inflections = set()
        for firstname in firstname_variants:
            for firstname2 in firstname2nd_variants:
                for surname in surname_variants:
                    expected_inflections.add(f"{firstname} {firstname2} {surname}, {generation_mark}")

        column_inflection = "/".join([f"{x}[k1gMnSc6]#jG" for x in firstname_variants])
        column_inflection += f" {'/'.join([f'{x}[k1gMnSc6]#jG' for x in firstname2nd_variants])}"
        column_inflection += f" {'/'.join([f'{x}[k1gMnSc6]#jS' for x in surname_variants])}"
        column_inflection += f", {generation_mark}#GS"

        self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def test_name_inflections_dotted(self) -> None:
        expected_basename = f"Hohenberg a.d.Eger"

        firstpart_variants = ["Hohenbergu", "Hohenbergerovi"]
        dotted_parts = ["a.", "d."]
        secondpart_variants = ["Egeru", "Egerovi", "Egru", "Egrovi"]

        expected_inflections = set()
        for first in firstpart_variants:
            for second in secondpart_variants:
                expected_inflections.add(f"{first} {''.join(dotted_parts)}{second}")

        column_inflection = "/".join([f"{x}[k1gMnSc6]#jL" for x in firstpart_variants])
        column_inflection += " "
        column_inflection += "".join([f"{x}#A" + u"\u200b" for x in dotted_parts])
        column_inflection += "/".join([f"{x}[kg1MnSc6]#jL" for x in secondpart_variants])

        self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def test_name_inflections_dotted_dashed_combination(self) -> None:
        expected_basename = "R.W. Seton-Watson"
        dotted_parts = ["R.", "W."]
        dashed_1st_part_variants = ["Setonu", "Setonovi"]
        dashed_2nd_part_variants = ["Watsonu", "Watsonovi"]

        expected_inflections = set()
        for dashed_1st in dashed_1st_part_variants:
            for dashed_2nd in dashed_2nd_part_variants:
                expected_inflections.add(f"{''.join(dotted_parts)} {dashed_1st}-{dashed_2nd}")

        column_inflection = "".join([f"{x}#I" + u"\u200b" for x in dotted_parts])
        column_inflection += " "
        column_inflection += "/".join([f"{x}[k1gMnSc6]#jS" for x in dashed_1st_part_variants])
        column_inflection += "-"
        column_inflection += "/".join([f"{x}[k1gMnSc6]#js" for x in dashed_2nd_part_variants])

        self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def test_name_inflections_dashed_bo_gdanovic(self) -> None:
        expected_basename = "Bogdan Bo­gdanović"
        firstname_variants = ["Bogdanovi", "Bogdanu"]
        surname_variants = ["Bo­gdanovićovi", "Bo­gdanovići"]

        expected_inflections = set()
        for first in firstname_variants:
            for second in surname_variants:
                expected_inflections.add(f"{first} {second}")

        column_inflection = "/".join([f"{x}[k1gMnSc3]#jG" for x in firstname_variants])
        column_inflection += " "
        column_inflection += "/".join([f"{x}[k1gMnSc3]#jS" for x in surname_variants])

        self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def test_name_inflections_dashed_hypotetic_bo_gda_novic_with_dashes_combination_of_marked_and_unmarked(self) -> None:
        firstname_variants = ["Bogdanovi", "Bogdanu"]
        surname_dashed1 = "Bo"
        surname_dashed2_variants = ["gda", "gdá"]
        dashed_variants = ["-", "–", "—", "­"]
        surname_dashed3_variants = ["novići", "novićovi"]

        for dash1 in dashed_variants:
            for dash2 in dashed_variants:
                expected_basename = f"Bogdan Bo{dash1}gda{dash2}nović"
                expected_inflections = set()
                for first in firstname_variants:
                    for middle in surname_dashed2_variants:
                        for last in surname_dashed3_variants:
                            expected_inflections.add(f"{first} {surname_dashed1}{dash1}{middle}{dash2}{last}")

                column_inflection = "/".join([f"{x}[k1gMnSc3]#jG" for x in firstname_variants])
                column_inflection += " "
                column_inflection += "/".join([f"{surname_dashed1}{dash1}{x}[k1gMnSc3]#jS" for x in surname_dashed2_variants])
                column_inflection += dash2
                column_inflection += "/".join([f"{x}[k1gMnSc3]#jS" for x in surname_dashed3_variants])

                self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def test_name_inflection_dashed_honore_charles_michel_joseph(self) -> None:
        expected_basename = "Honoré- -Charles-Michel-Joseph"
        #|Honorém[k1gMnSc6]#jG/Honoré[k1gMnSc6]#jG/Honoréovi[k1gMnSc6]#jG- -Charlesovi[k1gMnSc6]#jG/Charlesi[k1gMnSc6]#jG-Michelu[k1gMnSc6]#jG/Michelovi[k1gMnSc6]#jG-Josephovi[k1gMnSc6]#jS/Josephu[k1gMnSc6]#jS


    def _do_common_test(self, expected_basename: str, expected_inflections: Set[str], column_inflection: str) -> None:
        line = f"{expected_basename}\tcs\tP:::M\t{column_inflection}\t"

        test_basename, test_inflections, test_subnames = KB2namelist.process_name_inflections(line)

        self._print_debug(line=line, test_inflections=test_inflections, expected_inflections=expected_inflections)

        self.assertEqual(test_basename, expected_basename)
        self.assertEqual(test_inflections, expected_inflections)



    def _test_name_inflections_dash_delimiter(self, dash_delimiter: str) -> None:
        expected_basename = f"Adam{dash_delimiter}Philippe de Custine"

        firstname_variants = ["Adamu", "Adamovi"]
        surname1st_variants = ["Philippovi", "Philippemu"]
        surname_junction = "de"
        surname2nd_variants = ["Custinemu", "Custinu", "Custine", "Custinovi"]

        expected_inflections = set()
        for firstname in firstname_variants:
            for surname1 in surname1st_variants:
                for surname2 in surname2nd_variants:
                    expected_inflections.add(f"{firstname}{dash_delimiter}{surname1} {surname_junction} {surname2}")

        column_inflection = "/".join([f"{x}[k1gMnSc3]#jG" for x in firstname_variants])
        column_inflection += f"{dash_delimiter}{'/'.join([f'{x}[k1gMnSc3]#jS' for x in surname1st_variants])}"
        column_inflection += f" {surname_junction}#jS"
        column_inflection += f" {'/'.join([f'{x}[k1gMnSc3]#jS' for x in surname2nd_variants])}"

        self._do_common_test(expected_basename=expected_basename, expected_inflections=expected_inflections, column_inflection=column_inflection)


    def _print_debug(self, line: str, test_inflections: Set[str], expected_inflections: Set[str]) -> None:
        if self.PRINT_DEBUG == False:
            return

        print("SOURCE LINE")
        print(line)
        print()
        print("GIVEN INFLECTED VARIANTS:")
        print(test_inflections)
        print()
        print("EXPECTED INFLECTED VARIANTS:")
        print(expected_inflections)


if __name__ == "__main__":
    unittest.main()
