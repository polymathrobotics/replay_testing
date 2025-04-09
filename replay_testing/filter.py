# Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
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
