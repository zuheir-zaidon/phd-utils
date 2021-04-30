__version__ = "0.1.0"

from collections import deque
import logging
import subprocess
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
    command = ["convert"]
    sources = map(Path.as_posix, map(Path.absolute, sources))
    command.extend(sources)
    command.append(destination.absolute().as_posix())

    logger.debug(f"Issuing command {command}")
    subprocess.run(command)
