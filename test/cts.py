# -*- coding: utf-8 -*-
# 
from sys import argv, stdout, exit
import subprocess
import time

# Takes 4 parameters : uuid, repo, branch, dest
script, uuid, repo, branch, dest = tuple(argv)

print("Starting tests !", flush=True)

for i in range(1,20):
    print(str(i) + " Test", flush=True)
    time.sleep(1)

print("Finished tests !", flush=True)
