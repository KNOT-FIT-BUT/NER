import unittest

from unittest.mock import MagicMock

from src import KB2namelist, metrics_knowledge_base

class TestKB2namelist(unittest.TestCase):
    def setUp(self) -> None:
        KB2namelist.persons = KB2namelist.load_persons_module("cs")

    def test_name_inflections_Adam_Philippe_de_Custine(self) -> None:
        expected_basename = "Adam-Philippe de Custine"

        firstname_variants = ["Adamu", "Adamovi"]
        surname1st_variants = ["Philippovi", "Philippemu"]
        surname_junction = "de"
        surname2nd_variants = ["Custinemu", "Custinu", "Custine", "Custinovi"]

        expected_inflections = set()
        for firstname in firstname_variants:
            for surname1 in surname1st_variants:
                for surname2 in surname2nd_variants:
                    expected_inflections.add(f"{firstname}-{surname1} {surname_junction} {surname2}")

        column_inflection = "/".join([f"{x}[k1gMnSc3]#jG" for x in firstname_variants])
        column_inflection += f"-{'/'.join([f'{x}[k1gMnSc3]#jS' for x in surname1st_variants])}"
        column_inflection += f" {surname_junction}#jS"
        column_inflection += f" {'/'.join([f'{x}[k1gMnSc3]#jS' for x in surname2nd_variants])}"
        line = f"{expected_basename}\tcs\tP:::M\t{column_inflection}\t"
        print(line)
        print(expected_inflections)

        test_basename, test_inflections, test_subnames = KB2namelist.process_name_inflections(line)

        self.assertEqual(test_basename, expected_basename)
        self.assertEqual(test_inflections, expected_inflections)

    def test_name_inflections_Alfred_Pritchard_Sloan_Jr(self) -> None:
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
        line = f"{expected_basename}\tcs\tP:::M\t{column_inflection}\t"
        print(line)
        print(expected_inflections)

        test_basename, test_inflections, test_subnames = KB2namelist.process_name_inflections(line)

        self.assertEqual(test_basename, expected_basename)
        self.assertEqual(test_inflections, expected_inflections)

if __name__ == "__main__":
    unittest.main()
