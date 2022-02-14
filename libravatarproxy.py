#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import sys
import os

sys.stderr.buffer.write(
    b"%s" % bytes(os.environ.get("QUERY_STRING", "No Query String in url"), "utf-8")
)

link = "https://www.libravatar.org/avatar/%s" % os.environ.get("QUERY_STRING", "x" * 32)
sys.stderr.buffer.write(b"%s" % bytes(link, "utf-8"))

data = None
with urllib.request.urlopen(link) as f:
    data = f.read()

for header in f.headers._headers:
    if header[0] == "Content-Type":
        sys.stdout.buffer.write(
            b"%s: %s\n\n" % (bytes(header[0], "utf-8"), bytes(header[1], "utf-8"))
        )
        sys.stdout.flush()
        break

sys.stdout.buffer.write(data)
