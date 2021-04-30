#!/usr/bin/env python3

"""
Compiling m-images into n-folders
"""

import argparse
import logging

from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_folder", type=Path)
    parser.add_argument("-n", "--number-of-tifs-per-subfolder", type=int, default=2000)
    parser.add_argument(
        "-l",
        "--log-level",
        type=lambda x: getattr(logging, x.upper()),
        default=logging.INFO,
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    logger.debug(f"Arguments: {args}")

    source_folder: Path = args.source_folder

    assert source_folder.is_dir(), "The specified folder does not exist"

    logger.debug(f"Folder '{source_folder}' exists")

    experiment_folders: List[Path] = list()

    for path in source_folder.glob("Experiment-*/"):
        logger.debug(f"Checking globbed {path}")
        if path.is_dir():
            logger.debug(f"Adding path {path} to experiment_folders")
            experiment_folders.append(path)

    logger.debug(f"Discovered experiment folders: {experiment_folders}")

    for experiment_folder in experiment_folders:
        logger.info(f"Processing experiment folder {experiment_folder}")

        list_of_image_files = list(experiment_folder.glob("Experiment-*.tif"))

        number_of_image_files_processed_so_far = 0
        current_subfolder = experiment_folder.joinpath(
            f"{number_of_image_files_processed_so_far}"
        )

        current_subfolder.mkdir()

        for image in list_of_image_files:
            destination = current_subfolder.joinpath(image.name)

            logger.debug(f"Moving {image} to {destination}")

            image.rename(destination)

            number_of_image_files_processed_so_far += 1
            if (
                number_of_image_files_processed_so_far
                % args.number_of_tifs_per_subfolder
            ) == 0:
                current_subfolder = experiment_folder.joinpath(
                    f"{number_of_image_files_processed_so_far}"
                )

                logger.debug(
                    f"Processed {number_of_image_files_processed_so_far} images - create a new subfolder {current_subfolder}"
                )
                current_subfolder.mkdir()
