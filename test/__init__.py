# -*- coding: utf-8 -*-
# 
from collections import defaultdict
from sys import argv, stdout, exit
import subprocess
import time

import repo
import test


def prnt(data):
    print(data, flush=True)

# Takes 4 parameters : uuid, repo, branch, dest
script, opts, uuid, reponame, branch, dest = tuple(argv)
errors = False
directory = "/".join([dest, uuid])

if len(opts) > 1:
    opts = list(opts[1:])
else:   
    opts = list()

verbose = "v" in opts

# Store the results
results = defaultdict(dict)
passing = defaultdict(dict)

prnt(">>> Starting tests !")

for f in repo.find_files(directory):
    if f.endswith("__cts__.xml"):
        prnt(f + " is a metadata file")
    else:
        t = test.CTSUnit(f)
        prnt(">>>> Testing "+ f.split("data")[-1])
        for name, status, op in t.test():
            
            if status:
                status_str = " passed"
            else:
                status_str = " failed"

            prnt(">>>>> " +name + status_str)

            if verbose:
                prnt("\n".join([o for o in op]))

            results[f][name] = status


        passing[f.split("/")[-1]] = False not in results[f].values()




prnt(">>> Finished tests !")

success = len([True for status in passing.values() if status is True])
prnt("{0} over {1} texts have fully passed the tests".format(success, len(passing)))

if success != len(passing):
    exit(1)