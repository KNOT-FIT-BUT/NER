#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Typeflags format for person entities => <Type: P=Person>:<Subtype: F/G=Fictional/Group>:<Name type: <Empty>/N/P=May be regular name/Nickname/Pseudonym>:<Gender: F/M=Female/Male>
# TODO Mr. Dočekal: maybe P:F:..., P:G:..., P:FG:..., 
# TODO Mr. Dočekal: Location has second group (fictional / group)
# TODO: type artist?

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import argparse
import re

import metrics_knowledge_base
from libs.nationalities.nat_loader import NatLoader


# KB struct variable
kb_struct = None

# multiple values delimiter
KB_MULTIVALUE_DELIM = metrics_knowledge_base.KB_MULTIVALUE_DELIM

args = None
name_typeflag = []
nationalities = []

def extract_names_from_line(line):
    names = kb_struct.get_data_for(line, 'ALIASES').split(KB_MULTIVALUE_DELIM)
    names.append(f"{kb_struct.get_data_for(line, 'NAME')}#lang={args.lang}")
    names = (a for a in names if a.strip() != "")

    return names


def append_names_to_list(names, type_flags, url_origin):
    for n in names:
        n = re.sub('\s+', ' ', n).strip()
        name_parts = n.split("#", 1)
        if not name_parts[0]:
            continue
        name_type_flags = type_flags

        match = re.search(r"#ntype=([^|#]+).*$", n)
        if match and match.group(1):
            n = re.sub(r"#ntype=[^|#]+", "", n)
            flag_ntype = ''
            str_ntype = match.group(1)

            if str_ntype == 'nick':
                flag_ntype = 'N'
            elif str_ntype == 'pseudo':
                flag_ntype = 'P'
            name_type_flags = re.sub(r"(:[MF]?(?:\t|$))", flag_ntype + "\g<1>", name_type_flags)

        lang = ''
        match = re.search(r"#lang=([^|#]+).*$", n)
        if match and match.group(1):
            n = re.sub(r"#lang=[^|#]+", "", n)
            if (match.group(1) != "???"):
                lang = match.group(1)

        unsuitable = ";?!()[]{}<>/~@#$%^&*_=+|\"\\"
        for x in unsuitable:
            if x in n:
                break
        else:
            name_typeflag.append('\t'.join([n, lang, name_type_flags, url_origin]))



def generate_name_alternatives(kb_path):
    if kb_struct:
        for line in kb_struct.lines:
            ent_type_set = kb_struct.get_ent_type(line)
            names = extract_names_from_line(line)
            url_origin = kb_struct.get_data_for(line, 'WIKIPEDIA URL')

            subtype = ''
            if kb_struct.get_data_for(line, 'FICTIONAL') == 1:
                subtype += 'F'
            if 'group' in ent_type_set:
                subtype += 'G'

            subtype = ''.join(sorted(subtype))
            if 'person' in ent_type_set:
                gender = kb_struct.get_data_for(line, 'GENDER')
                append_names_to_list(names, 'P:' + subtype + '::' + gender, url_origin)
            elif 'geographical' in ent_type_set:
                append_names_to_list(names, 'L' + (':{}'.format(subtype) if subtype else ''), url_origin)
            else:
                continue;

        for n in name_typeflag:
            print(n)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--kb_path', help = 'Path of Knowledge base.')
    parser.add_argument('-l', '--lang', help = 'Language to process.')
    args = parser.parse_args()

    nationalities = NatLoader.load(args.lang).get_nationalities()
    kb_struct =  metrics_knowledge_base.KnowledgeBase(lang = args.lang, path_to_kb = args.kb_path)
    kb_struct.check_or_load_kb()

    generate_name_alternatives(args.kb_path)
