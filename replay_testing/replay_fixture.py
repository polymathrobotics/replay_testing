from .models import McapFixture
from .utils import find_mcap_files
from pathlib import Path
import shutil

from .reader import get_message_mcap_reader

# Class responsible for managing all replay fixtures


class ReplayFixture:
    input_fixture: McapFixture = None
    filtered_fixture: McapFixture = None
    run_fixtures: list[McapFixture] = None

    base_path: str

    def __init__(self, base_folder: str, fixture: McapFixture):
        self.run_fixtures = []
        self.base_path = base_folder
        self.input_fixture = fixture
        self.filtered_fixture = McapFixture(
            path=self.base_path + "/filtered_fixture.mcap"
        )

    def cleanup_run_fixtures(self):
        print("length of fixtures: ", len(self.run_fixtures))
        for run_fixture in self.run_fixtures:
            mcap_folder = run_fixture.path
            # TODO(troy): cleanup this HACK
            mcap_files = find_mcap_files(mcap_folder)
            if len(mcap_files) == 0:
                raise ValueError(f"No mcap files found in {mcap_folder}")
            mcap_file_path = mcap_files[0]
            new_path = shutil.move(mcap_file_path, Path(mcap_folder).parent)
            shutil.rmtree(mcap_folder)

            run_fixture.path = new_path

    def initialize_run_reader(self):
        self.run_fixture.reader = get_message_mcap_reader(
            self.run_fixture.path
        )
