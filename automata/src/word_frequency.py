import json

from dataclasses import dataclass
from os import access, R_OK, remove
from typing import Dict, Optional


@dataclass
class FrequencyMeasures:
    all: float
    uplow: float


class WordFrequency:
    input: str

    def __init__(self, filepath: str) -> None:
        if not access(filepath, R_OK):
            raise WordFrequencyInputNotReadable()
        self.input = filepath

    def load_frequency(
        self, outfile: Optional[str] = None, clean_cached: Optional[bool] = False
    ) -> Dict[str, FrequencyMeasures]:
        if not outfile:
            return self._count_frequency()

        try:
            if clean_cached == True:
                remove(outfile)
                return self._generate_frequency(outfile=outfile)
        except FileNotFoundError:
            ...

        try:
            fout = open(outfile, "r")
        except FileNotFoundError:
            return self._generate_frequency(outfile=outfile)
        else:
            with fout:
                data = {}
                json_data = json.load(fout)
                for k, v in json_data.items():
                    if "all" not in v:
                        v["all"] = 0
                    if "uplow" not in v:
                        v["uplow"] = 0
                    data[k] = FrequencyMeasures(**v)
                return data

    def _count_frequency(self) -> Dict[str, FrequencyMeasures]:
        with open(self.input, errors="ignore") as fin:
            word_count: dict[str, int] = {}
            word_count_all: dict[str, int] = {}
            word_count_uplow: dict[str, int] = {}
            word_frequency: dict[str, FrequencyMeasures] = {}

            for line in fin:
                # must be rstrip() only due to space as a key in input file
                try:
                    word, count = line.rstrip().split("\t")
                    count = int(count)
                except ValueError:
                    raise WordFrequencyInputBadFormat()
                if word not in word_count:
                    word_count[word] = count
                else:
                    word_count[word] += count

                base_word = word.lower()
                if base_word not in word_count_all:
                    word_count_all[base_word] = 0
                    word_count_uplow[base_word] = 0

                word_count_all[base_word] += count
                if word in [word.lower(), word.title()]:
                    word_count_uplow[base_word] += count

            for word, count in word_count.items():
                base_word = word.lower()
                freqs = FrequencyMeasures(
                    count / word_count_all[base_word]
                    if word_count_all[base_word] > 0
                    else 0,
                    count / word_count_uplow[base_word]
                    if word_count_uplow[base_word] > 0
                    and word in [word.lower(), word.title()]
                    else 0,
                )
                word_frequency[word] = freqs

            return word_frequency

    def _generate_frequency(self, outfile: str) -> Dict[str, FrequencyMeasures]:
        word_frequency = self._count_frequency()
        with open(outfile, "w") as fout:
            json.dump(
                word_frequency,
                fout,
                default=lambda o: dict(
                    (key, value) for key, value in o.__dict__.items() if value
                ),
                ensure_ascii=False,
            )
        return word_frequency


class WordFrequencyInputNotReadable(Exception):
    ...


class WordFrequencyInputBadFormat(Exception):
    ...
