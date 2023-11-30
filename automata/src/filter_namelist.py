#!/usr/bin/env python

import sys

kb_file_name = sys.argv[1]
namelist_file_name = sys.argv[2]

kb_dictionary = set()

f1 = open(kb_file_name, "r")
i = 1
for line in f1:
    if len(line.rstrip()) > 0:
        kb_dictionary.add(i)
    i += 1

f2 = open(namelist_file_name, "r")
for line in f2:
    fields = line.rstrip().split("\t")
    entities = fields[1].split(";")
    output = ""
    for e in entities:
        if e == "N":
            output += ";"+e
        elif int(e) in kb_dictionary:
            output += ";"+e
    print(fields[0]+"\t"+output[1:])

