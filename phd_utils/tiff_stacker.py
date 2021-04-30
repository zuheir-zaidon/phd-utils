import argparse
import logging
import subprocess

from collections import deque
from pathlib import Path
from typing import Iterable, Iterator, List

from IPython.lib.pretty import pretty as pformat

from .third_party import grouper

logger = logging.getLogger(__name__)


def stack_in_folders(folders: Iterator[Path], files_per_stack: int):
    """For each folder, discover all TIF files, and combine them into stacks comprising of the contents of N of those files

    Args:
        folders (Iterator[Path]): The folders to search for TIFs in. The final folder will contain the stacks, with the originals removed
        frames_per_stack (int): How many files to combine into each stack
    """
    folders = list(filter(Path.is_dir, folders))
    logger.debug(f"Creating stacks from contents of each folder in {folders}")

    for folder in folders:
        tifs = list(filter(Path.is_file, folder.glob("**/*.tif")))
        tifs.sort()

        logger.info(f"Found {len(tifs)} TIFs in {folder}")

        logger.debug(f"TIFs:\n{pformat(tifs, max_seq_length=10)}")

        for group_number, group in enumerate(
            grouper(iterable=tifs, group_size=files_per_stack)
        ):
            group: List[Path] = list(group)
            stack = folder / f"stack{group_number}.tif"
            logger.info(
                f"Making a stacking from {group[0]} to {group[-1]} into {stack}"
            )

            stack_tifs(group, stack)

            # Now delete all the files
            deque(map(Path.unlink, group))


def stack_tifs(sources: Iterable[Path], destination: Path):
    """Call out to imagemagick to do the stacking

    Args:
        sources (Iterable[Path]): Images to stack from
        destination (Path): Image to stack to
    """
    command = ["convert"]
    sources = map(Path.as_posix, map(Path.absolute, sources))
    command.extend(sources)
    command.append(destination.absolute().as_posix())

    logger.debug(f"Issuing command {command}")

    subprocess.run(
        command, check=True
    )  # TODO there is a more pythonic way of doing this


def main():
    parser = argparse.ArgumentParser(
        description="""
    Given a list of directories this program will
    - Gather all files that end in .tif
    - Sort them lexicographically
    - Merge FILES_PER_STACK of them into a single "stackN.tif" file into that directory (where N is the current batch), for all files
    - Delete the original files

    It calls `convert`, with the assumption that it is ImageMagick. Ensure that ImageMagick is installed
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("folder", type=Path, nargs="+")
    parser.add_argument(
        "-f",
        "--files-per-stack",
        type=int,
        default=2000,
        help="Number of frames to put in each stack",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=lambda x: getattr(logging, x.upper()),
        default=logging.INFO,
        help="How verbose to be",
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    logger.debug(f"Arguments: {args}")

    stack_in_folders(folders=args.folder, files_per_stack=args.files_per_stack)
