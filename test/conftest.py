# conftest.py
import logging
import pytest


@pytest.fixture(autouse=True)
def configure_logging():
    logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
