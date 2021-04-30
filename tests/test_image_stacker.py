from pathlib import Path
from IPython.lib.pretty import pretty as pformat
import image_stacker as subject

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
    subject.stack_in_folders(folders=[experiment_folder], frames_per_stack=200)
    contents = list(map(lambda p: p.name, experiment_folder.iterdir()))
    contents.sort()
    logger.debug(f"Contents of folder:\n{pformat(contents)}")
    assert contents == ["stack0.tif", "stack1.tif", "stack2.tif"]


def test_stack_tifs(assets: Path):
    sources = list(assets.iterdir())
    sources.sort()
    subject.stack_tifs(sources=sources, destination=assets / "stack0.tif")
