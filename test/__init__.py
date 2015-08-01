# -*- coding: utf-8 -*-
# 
from sys import argv, stdout, exit
import subprocess
import time

import repo
import test


def prnt(data):
    print(data, flush=True)

# Takes 4 parameters : uuid, repo, branch, dest
script, uuid, reponame, branch, dest = tuple(argv)
errors = False
directory = "/".join([dest, uuid])

prnt(">>> Starting tests !")

for f in repo.find_files(directory):
    if f.endswith("__cts__.xml"):
        prnt(f + " is a metadata file")
    else:
        t = test.CTSUnit(f)
        prnt(">>>> Testing "+ f.split("data")[-1])
        for name, status, op in t.test():
            
            if status:
                status = " passed"
            else:
                status = " failed"

            prnt(">>>>> " +name + status)
            prnt("\n".join([o for o in op]))



prnt(">>> Finished tests !")
