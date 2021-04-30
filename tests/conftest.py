import pytest
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def assets() -> Path:
    folder = Path(__file__).parent / "assets"
    assert folder.is_dir()
    return folder
