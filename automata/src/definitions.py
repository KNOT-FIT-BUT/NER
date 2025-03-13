#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import regex

# 0x2D (0045), 0x96 (0150), 0x97 (0151), 0xAD (0173)
DASHES = "-–—­"
RE_DASHES = regex.escape(DASHES)
RE_DASHES_VARIANTS = r"[%s]" % DASHES
