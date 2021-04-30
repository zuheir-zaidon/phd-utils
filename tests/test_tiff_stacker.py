import filecmp
import logging
import shutil
from pathlib import Path
from typing import Iterable

import phd_utils.tiff_stacker as subject
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture
def single_images(assets: Path) -> Iterable[Path]:
    files = [path for path in assets.iterdir() if path.name.startswith("single")]
    files.sort()
    return files


@pytest.fixture
def correctly_stacked(assets: Path):
    return assets / "stacked.tif"


@pytest.fixture
def experiment_folder(single_images: Iterable[Path], tmp_path: Path):
    for image in single_images:
        shutil.copy(image, tmp_path)
    return tmp_path


def test_stack_tifs(
    single_images: Iterable[Path], correctly_stacked: Path, tmp_path: Path
):
    destination = tmp_path / "stacked.tif"
    subject.stack_tifs(sources=single_images, destination=destination)
    assert filecmp.cmp(correctly_stacked, destination, shallow=False)


def test_stack_in_folders(experiment_folder: Path):
    subject.stack_in_folders([experiment_folder], files_per_stack=2)
    assert len(list(experiment_folder.iterdir())) == 3
