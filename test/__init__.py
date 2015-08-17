# -*- coding: utf-8 -*-

from collections import defaultdict
from sys import argv, stdout, exit
import subprocess
import time
import concurrent.futures

import repo
import test
import json
import statistics

inv = []

def cover(test):
    """ Given a dictionary, compute the coverage of one item 

    :param test: Dictionary where keys represents test done on a file and value a boolean indicating passing status 
    :type test: boolean

    :returns: Passing status 
    :rtype: dict

    """ 
    results = list(test.values())
    return {
        "units" : test,
        "coverage" : len([v for v in results if v is True])/len(results)*100,
        "status" : False not in results
    }

def prnt(data):
    """ Print data and flush the stdout to be able to retrieve information line by line on another tool

    :param data: Data to be printed
    :type data: str

    """
    print(data.replace(directory, reponame), flush=True)


def do_test(f, tei, epidoc, verbose, inventory=None):
    """ Do test for a file and print the results

    :param f: Path of the file to be tested
    :type f: str

    :returns: List of status informations
    :rtype: list
    """
    logs = []
    if not inventory:
        inventory = []
    if f.endswith("__cts__.xml"):
        t = test.INVUnit(f)
        logs.append(">>>> Testing "+ f)

        for name, status, op in t.test():
            
            if status:
                status_str = " passed"
            else:
                status_str = " failed"

            logs.append(">>>>> " +name + status_str)

            if verbose:
                logs.append("\n".join([o for o in op]))

            results[f][name] = status

        results[f] = cover(results[f])
        passing[f.replace("/", ".")] = True == results[f]["status"]
        inventory += t.urns

    else:
        t = test.CTSUnit(f)
        logs.append(">>>> Testing "+ f.split("data")[-1])
        for name, status, op in t.test(tei, epidoc, inventory):
            
            if status:
                status_str = " passed"
            else:
                status_str = " failed"

            logs.append(">>>>> " +name + status_str)

            if verbose:
                logs.append("\n".join([o for o in op]))

            results[f][name] = status

        results[f] = cover(results[f])
        passing[f.split("/")[-1]] = True == results[f]["status"]

    return logs + ["test+=1"], inventory

"""
    Initialization and parameters recovering
"""
# Takes 4 parameters : uuid, repo, branch, dest
script, opts, uuid, reponame, branch, dest = tuple(argv)
errors = False
directory = "/".join([dest, uuid])

if len(opts) > 1:
    opts = list(opts[1:])
else:   
    opts = list()

verbose = "v" in opts
tei = "t" in opts
epidoc = "e" in opts
""" 
    Results storing variables initialization
"""

# Store the results
results = defaultdict(dict)
passing = defaultdict(dict)

files, cts__ = repo.find_files(directory)

prnt(">>> Starting tests !")
prnt("files="+str(len(files) + len(cts__)))

# We load a thread pool which has 5 maximum workers
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # We create a dictionary of tasks which 
    tasks = {executor.submit(do_test, target_file, tei, epidoc, verbose, inv): target_file for target_file in cts__}
    # We iterate over a dictionary of completed tasks
    for future in concurrent.futures.as_completed(tasks):
        logs, inv = future.result()
        for log in logs:
            prnt(log)

# We load a thread pool which has 5 maximum workers
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # We create a dictionary of tasks which 
    tasks = {executor.submit(do_test, target_file, tei, epidoc, verbose, inv): target_file for target_file in files}
    # We iterate over a dictionary of completed tasks
    for future in concurrent.futures.as_completed(tasks):
        logs, inv = future.result()
        for log in logs:
            prnt(log)

prnt(">>> Finished tests !")

success = len([True for status in passing.values() if status is True])
if success == len(passing):
    status_string = "success"
else:
    status_string = "failure"
prnt("[{2}] {0} over {1} texts have fully passed the tests".format(success, len(passing), status_string))

prnt("====JSON====")
prnt(json.dumps({
    "status" : success == len(passing),
    "units" : results,
    "coverage" : statistics.mean([test["coverage"] for test in results.values()])
}))

if success != len(passing):
    exit(1)
else:
    exit(0)