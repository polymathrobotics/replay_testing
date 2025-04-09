# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
import os


def find_mcap_files(input_dir):
    """Recursively find all .mcap files in the input directory."""
    mcap_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".mcap"):
                mcap_files.append(os.path.join(root, file))
    return mcap_files
