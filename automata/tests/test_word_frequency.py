from glob import glob
from os import makedirs, remove
from os.path import basename, dirname, getmtime, join as path_join
from shutil import rmtree
from typing import Dict, Optional
from unittest import TestCase

from automata.src.word_frequency import (
    FrequencyMeasures,
    WordFrequency,
    WordFrequencyInputBadFormat,
    WordFrequencyInputNotReadable,
)


class TestWordFrequency(TestCase):
    _file_basename: str = "test_word_frequency"

    _default_data: Dict[str, int] = {
        "tEst": 1,
        "TeSt": 1,
        "TEST": 5,
        "Test": 10,
        "test": 100,
    }

    @classmethod
    def setUpClass(cls) -> None:
        makedirs(cls._get_files_basedir(), exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            rmtree(cls._get_files_basedir())
        except FileNotFoundError:
            ...

    def tearDown(self) -> None:
        for filename in glob(path_join(self._get_files_basedir(), "*")):
            remove(filename)

    def test_input_found(self) -> None:
        basedir = self._get_files_basedir()
        self.assertEqual([], self._listdir(dir=basedir))
        wf = self._get_word_frequency_instance()
        self.assertEqual([self._get_infile_path()], self._listdir(dir=basedir))

    def test_input_not_found(self) -> None:
        self.assertRaises(
            WordFrequencyInputNotReadable,
            WordFrequency,
            path_join(self._get_files_basedir(), "FileNotExists.not-exists"),
        )

    def test_count_frequency_all(self) -> None:
        data = self._count_frequency()
        self._assert_count_frequency_all(data=data)

    def test_count_frequency_uplow(self) -> None:
        data = self._count_frequency()
        self._assert_count_frequency_uplow(data=data)

    def test_count_frequency_upper_only(self) -> None:
        infile = self._get_infile_path()
        input_data = {"teST": 5, "Test": 10}
        self._init_input_file(infile=infile, data=input_data)
        wf = WordFrequency(infile)
        data = wf._count_frequency()
        with self.subTest("key \"Test\""):
            self.assertEqual(1.0, data["Test"].uplow)
        with self.subTest("key \"teST\""):
            self.assertEqual(0.0, data["teST"].uplow)
        with self.subTest("key \"test\""):
            self.assertEqual(False, "test" in data)

    def test_count_frequency_zero(self) -> None:
        infile = self._get_infile_path()
        input_data = {"test": 0, "Test": 0}
        self._init_input_file(infile=infile, data=input_data)
        wf = WordFrequency(infile)
        data = wf._count_frequency()
        for tested_key in input_data.keys():
            with self.subTest("uplow variants frequency"):
                self.assertEqual(0, data[tested_key].uplow)
            with self.subTest("all variants frequency"):
                self.assertEqual(0, data[tested_key].all)

    def test_count_frequency_multiple_lines(self) -> None:
        infile = self._get_infile_path()
        with open(infile, "w") as ftest:
            ftest.write("test\t4\n")
            ftest.write("test\t6\n")
            ftest.write("Test\t10\n")
            ftest.write("Test\t7\n")
            ftest.write("Test\t3\n")
            ftest.write("tESt\t3\n")
            ftest.write("tESt\t4\n")
            ftest.write("tEST\t3\n")
        wf = WordFrequency(infile)
        data = wf._count_frequency()
        with self.subTest("uplow variants frequency for key \"test\""):
            self.assertEqual(1/3, data["test"].uplow, data)
        with self.subTest("uplow variants frequency for key \"Test\""):
            self.assertEqual(2/3, data["Test"].uplow, data)
        with self.subTest("all variants frequency for key \"test\""):
            self.assertEqual(1/4, data["test"].all, data)
        with self.subTest("all variants frequency for key \"Test\""):
            self.assertEqual(1/2, data["Test"].all, data)

    def test_count_frequency_bad_file_format(self) -> None:
        self._test_count_frequency_bad_format(file_content="test")

    def test_count_frequency_no_number_in_wordcount(self) -> None:
        self._test_count_frequency_bad_format(file_content="test\tjedna")

    def test_load_frequency_without_arg(self) -> None:
        data = self._test_first_load_frequency_with_arg()
        self.assertEqual(
            [self._get_infile_path()], self._listdir(dir=self._get_files_basedir())
        )

    def test_load_frequency_arg_output_not_exists(self) -> None:
        outfile = self._get_outfile_path()
        data = self._test_first_load_frequency_with_arg(arg=outfile)
        self.assertEqual(
            [self._get_infile_path(), outfile],
            self._listdir(dir=self._get_files_basedir()),
        )

    def test_load_frequency_arg_output_exists(self) -> None:
        outfile = self._get_outfile_path()
        previously_modified = (
            self._test_load_frequency_arg_output_exists_return_its_first_modify(
                outfile=outfile,
                clean_cached=False,
            )
        )
        self.assertEqual(previously_modified, getmtime(outfile))

    def test_load_frequency_arg_output_exists_clean_cached(self) -> None:
        outfile = self._get_outfile_path()
        previously_modified = (
            self._test_load_frequency_arg_output_exists_return_its_first_modify(
                outfile=outfile,
                clean_cached=True,
            )
        )
        self.assertNotEqual(previously_modified, getmtime(outfile))

    @classmethod
    def _get_files_basedir(cls) -> str:
        basedir = dirname(dirname(__file__))
        return path_join(basedir, "tests", "tmp", "word_frequency")

    @classmethod
    def _get_infile_path(cls) -> str:
        return path_join(cls._get_files_basedir(), f"{cls._file_basename}.in")

    @classmethod
    def _get_outfile_path(cls) -> str:
        return path_join(cls._get_files_basedir(), f"{cls._file_basename}.out")

    @classmethod
    def _init_input_file(
        cls, infile: str, data: Optional[Dict[str, int]] = None
    ) -> None:
        if data is None:
            data = cls._default_data
        with open(infile, "w") as ftest:
            for k, v in data.items():
                ftest.write(f"{k}\t{v}\n")

    @classmethod
    def _listdir(cls, dir: str) -> None:
        return glob(path_join(dir, "*"))

    def _assert_count_frequency_all(self, data: Dict[str, FrequencyMeasures]) -> None:
        divider = 0
        for k, v in self._default_data.items():
            divider += v
        self.assertEqual(117, divider)
        for k, v in data.items():
            with self.subTest(f"key \"{k}\""):
                self.assertEqual(self._default_data[k] / divider, data[k].all)

    def _assert_count_frequency_uplow(self, data: Dict[str, FrequencyMeasures]) -> None:
        divider = self._default_data["test"] + self._default_data["Test"]
        self.assertEqual(110, divider)
        for tested_key in ["test", "Test"]:
            with self.subTest(f"key \"{tested_key}\""):
                self.assertEqual(
                    self._default_data[tested_key] / divider, data[tested_key].uplow
                )
        with self.subTest("key \"TEST\""):
            self.assertEqual(0, data["TEST"].uplow)

    def _get_word_frequency_instance(self) -> WordFrequency:
        infile = self._get_infile_path()
        self._init_input_file(infile=infile)
        return WordFrequency(infile)

    def _count_frequency(self) -> Dict[str, FrequencyMeasures]:
        wf = self._get_word_frequency_instance()
        return wf._count_frequency()

    def _test_count_frequency_bad_format(self, file_content: str) -> None:
        filepath = path_join(self._get_files_basedir(), f"{self._file_basename}.bad")
        with open(filepath, "w") as f:
            f.write(file_content)
        wf = WordFrequency(filepath)
        self.assertRaises(WordFrequencyInputBadFormat, wf._count_frequency)

    def _test_first_load_frequency_with_arg(
        self, arg: Optional[str] = None
    ) -> Dict[str, FrequencyMeasures]:
        self.assertEqual(0, len(self._listdir(dir=self._get_files_basedir())))

        wf = self._get_word_frequency_instance()
        with self.subTest("check of existing files"):
            self.assertEqual(
                [self._get_infile_path()], self._listdir(dir=self._get_files_basedir())
            )

        data = wf.load_frequency(outfile=arg)
        with self.subTest("uplow variants frequency"):
            self._assert_count_frequency_uplow(data=data)
        with self.subTest("all variants frequency"):
            self._assert_count_frequency_all(data=data)

        return data

    def _test_load_frequency_arg_output_exists_return_its_first_modify(
        self, outfile: str, clean_cached: bool = False
    ) -> float:
        self._test_first_load_frequency_with_arg(arg=outfile)
        self.assertEqual(
            [self._get_infile_path(), outfile],
            self._listdir(dir=self._get_files_basedir()),
        )

        dump_modify = getmtime(outfile)

        wf = self._get_word_frequency_instance()
        data = wf.load_frequency(outfile=outfile, clean_cached=clean_cached)

        with self.subTest("uplow variants frequency"):
            self._assert_count_frequency_uplow(data=data)
        with self.subTest("all variants frequeny"):
            self._assert_count_frequency_all(data=data)
        with self.subTest("check of existing files"):
            self.assertEqual(
                [self._get_infile_path(), outfile],
                self._listdir(dir=self._get_files_basedir()),
            )

        return dump_modify
