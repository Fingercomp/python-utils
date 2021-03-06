#!/usr/bin/env python3

import os
import sys
import shutil

if len(sys.argv) == 1 or len(sys.argv) > 5:
    print("USAGE: " + sys.argv[0] + " [file with mappings] [path to sources] "
          "[output path] (optional extension)")
    sys.exit(0)

mappingsfile = open(sys.argv[1]).readlines()
sources = sys.argv[2]
output = sys.argv[3]

mappings = {}

for line in mappingsfile:
    values = line.split(",")
    mappings[values[0]] = values[1]

if not sources == output:
    shutil.copytree(sources, output)

for root, dirs, files in os.walk(output):
    try:
        os.mkdir(root)
    except:
        pass
    for name in files:
        skip = False
        if len(sys.argv) == 5:
            if name[-len(sys.argv[4]):] != sys.argv[4]:
                skip = True
        if not skip:
            try:
                f = open(os.path.join(root, name), "r")
                content = f.read()
                f.close()
                for mapping in mappings:
                    content = content.replace(mapping, mappings[mapping])
                f = open(os.path.join(root, name), "w")
                f.write(content)
                f.close()
            except:
                pass


# vim: autoindent tabstop=4 shiftwidth=4 expandtab:
