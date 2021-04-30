#!/usr/bin/env python3


import argparse
import logging
from pathlib import Path


from . import stack_in_folders

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(
    description="""
Given a list of directories, grab all the tiff files in those directories, sort them, and collapse them into stacks with N frames per stack
"""
)
parser.add_argument("folder", type=Path, nargs="*")
parser.add_argument(
    "-f",
    "--frames-per-stack",
    type=int,
    default=2000,
    help="Number of frames to put in each stack",
)
parser.add_argument(
    "-l",
    "--log-level",
    type=lambda x: getattr(logging, x.upper()),
    default=logging.INFO,
)
args = parser.parse_args()

logging.basicConfig(level=args.log_level)

logger.debug(f"Arguments: {args}")

stack_in_folders(folders=args.folder, frames_per_stack=args.frames_per_stack)
