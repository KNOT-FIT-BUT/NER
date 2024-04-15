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
        self.assertEqual(1.0, data["Test"].uplow)
        self.assertEqual(0.0, data["teST"].uplow)
        self.assertEqual(False, "test" in data)

    def test_count_frequency_zero(self) -> None:
        infile = self._get_infile_path()
        input_data = {"test": 0, "Test": 0}
        self._init_input_file(infile=infile, data=input_data)
        wf = WordFrequency(infile)
        data = wf._count_frequency()
        for tested_key in input_data.keys():
            self.assertEqual(0, data[tested_key].uplow)
            self.assertEqual(0, data[tested_key].all)

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
            self.assertEqual(self._default_data[k] / divider, data[k].all)

    def _assert_count_frequency_uplow(self, data: Dict[str, FrequencyMeasures]) -> None:
        divider = self._default_data["test"] + self._default_data["Test"]
        self.assertEqual(110, divider)
        for tested_key in ["test", "Test"]:
            self.assertEqual(
                self._default_data[tested_key] / divider, data[tested_key].uplow
            )
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
        self.assertEqual(
            [self._get_infile_path()], self._listdir(dir=self._get_files_basedir())
        )

        data = wf.load_frequency(outfile=arg)
        self._assert_count_frequency_uplow(data=data)
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

        self._assert_count_frequency_uplow(data=data)
        self._assert_count_frequency_all(data=data)
        self.assertEqual(
            [self._get_infile_path(), outfile],
            self._listdir(dir=self._get_files_basedir()),
        )

        return dump_modify
