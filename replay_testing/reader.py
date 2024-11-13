import rosbag2_py
from mcap_ros2.reader import make_reader, McapReader
from mcap_ros2.decoder import DecoderFactory

# TODO: Figure out how to consolidate the two readers


def get_sequential_mcap_reader(mcap_path):
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=mcap_path, storage_id="mcap"),
        rosbag2_py.ConverterOptions(
            input_serialization_format="cdr", output_serialization_format="cdr"
        ),
    )
    return reader


def get_message_mcap_reader(mcap_path) -> McapReader:
    file = open(mcap_path, "rb")
    reader = make_reader(file, decoder_factories=[DecoderFactory()])
    return reader
