# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
import subprocess


def filter_mcap(input, output, output_topics):
    command = [
        "mcap",
        "filter",
        input,
        "-o",
        output,
    ]

    # Filter out topics that will be replayed
    for topic in output_topics:
        command.extend(["-n", topic])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error filtering {input}: {e}")
