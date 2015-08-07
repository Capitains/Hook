import os
import glob

def find_files(directory):
    return glob.glob(os.path.join(directory, "data/*/*/*.xml")) + glob.glob(os.path.join(directory, "data/*/*.xml"))