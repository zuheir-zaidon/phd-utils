__version__ = "0.1.0"

from collections import deque
from pathlib import Path
from typing import Iterable, Iterator, List
import logging
from IPython.lib.pretty import pretty as pformat
from .third_party import grouper

logger = logging.getLogger(__name__)


def stack_in_folders(folders: Iterator[Path], frames_per_stack: int):
    folders = list(filter(Path.is_dir, folders))
    logger.debug(f"Creating stacks from contents of each folder in {folders}")

    for folder in folders:
        tifs = list(filter(Path.is_file, folder.glob("**/*.tif")))
        tifs.sort()

        logger.info(f"Found {len(tifs)} TIFs in {folder}")

        logger.debug(f"TIFs:\n{pformat(tifs, max_seq_length=10)}")

        for group_number, group in enumerate(
            grouper(iterable=tifs, group_size=frames_per_stack)
        ):
            group: List[Path] = list(group)
            logger.debug(
                f"Making a stack of length {len(group)} from {group[0]} to {group[-1]}"
            )
            stack = folder / f"stack{group_number}.tif"
            stack_tifs(group, stack)


def stack_tifs(source: Iterable[Path], destination: Path):
    destination.touch()
    deque(map(Path.unlink, source))
