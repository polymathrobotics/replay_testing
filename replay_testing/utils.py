import os


def find_mcap_files(input_dir):
    """Recursively find all .mcap files in the input directory."""
    mcap_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".mcap"):
                mcap_files.append(os.path.join(root, file))
    return mcap_files
