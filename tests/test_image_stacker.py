from pathlib import Path
from typing import Iterable
from IPython.lib.pretty import pretty as pformat
import image_stacker as subject
import filecmp

import pytest
import logging

logger = logging.getLogger(__name__)


def fill_folder_with_images(folder: Path, number_of_images: int):
    images = [
        folder / f"Experiment-399-Image Export-13_t{x:05}.tif"
        for x in range(number_of_images)
    ]
    for image in images:
        image.touch()

    contents = list(folder.iterdir())
    contents.sort()

    logger.debug(f"{pformat(contents, max_seq_length=10)}")

    return folder


def test_stack_in_folders(tmp_path: Path):
    experiment_folder = fill_folder_with_images(folder=tmp_path, number_of_images=500)
    subject.stack_in_folders(folders=[experiment_folder], files_per_stack=200)
    contents = list(map(lambda p: p.name, experiment_folder.iterdir()))
    contents.sort()
    logger.debug(f"Contents of folder:\n{pformat(contents, max_seq_length=10)}")
    assert contents == ["stack0.tif", "stack1.tif", "stack2.tif"]


@pytest.fixture
def pre_stacked(assets: Path) -> Iterable[Path]:
    files = [path for path in assets.iterdir() if path.name.startswith("Experiment")]
    files.sort()
    return files


@pytest.fixture
def stacked(assets: Path):
    return assets / "stacked.tif"


def test_stack_tifs(pre_stacked: Iterable[Path], stacked: Path, tmp_path: Path):
    destination = tmp_path / "stacked.tif"
    subject.stack_tifs(sources=pre_stacked, destination=destination)
    assert filecmp.cmp(stacked, destination, shallow=False)
