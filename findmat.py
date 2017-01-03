import os
import re


def all_mats(prefix):
    """

    :return:  *_n.mat
    """
    mat_files = []
    pattern_mat = re.compile(prefix + r"_[0-9]+.mat")
    for root, dirs, files in os.walk("."):
        for filename in files:
            match = pattern_mat.match(filename)
            if match:
                mat_files.append(root + os.sep + filename)

    return mat_files

