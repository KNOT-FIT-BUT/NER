#!/bin/bash

grep '^[a-z]' $1 | sed 's|.*\t\(https://...wikipedia.org/wiki/[^\t]*\)\t.*|\1|g' | sed 's/^[^h].*//g' > KB.wiki
grep -P "\t.*N.*$" $2 > namelist.N
grep -v -P "\t.*N.*$" $2 > namelist.rest

./filter_namelist.py KB.wiki namelist.N > namelist.filtered

LC_ALL=C sort -m namelist.filtered namelist.rest

rm KB.wiki
rm namelist.N
rm namelist.rest
rm namelist.filtered
