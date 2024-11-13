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
