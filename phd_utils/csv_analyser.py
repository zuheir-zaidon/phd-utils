import logging
import argparse
from pathlib import Path
import pandas as pd
import string

logger = logging.getLogger(__name__)


def read_displacement_csv(path: Path):
    """Reads in a CSV, returning a dataframe with:
    - Frame (index)
    - X_Displacement
    - Y_Displacement

    Args:
        path (Path): Where the file is

    Returns:
        pd.DataFrame: A DataFrame (tabular data)
    """
    df: pd.DataFrame = pd.read_csv(
        path,
        names=[s for s in string.ascii_uppercase],  # A..Z
    )

    df.dropna(
        axis="index",  # Drop empty rows
        how="all",  # If all of their cells are empty
        inplace=True,
    )

    df.dropna(
        axis="columns",
        how="all",
        inplace=True,
    )

    df.rename(
        columns={
            "H": "Frame",
            "E": "X_Displacement",
            "F": "Y_Displacement",
        },
        inplace=True,
    )

    # Pandas interpreted this as a float. Fix that now, and set it as the index
    df["Frame"] = df["Frame"].astype(int)
    df.set_index("Frame", inplace=True)

    df.drop(
        # We've pulled out all of the columns we want, so drop the ones that we don't need (which have single-character names)
        labels=[col for col in df.columns if len(col) == 1],
        axis="columns",
        inplace=True,
    )

    return df


def calculate_substrate_displacement(
    reference: pd.DataFrame,
    substrate: pd.DataFrame,
):
    reference = reference.add_prefix("Reference_")
    substrate = substrate.add_prefix("Substrate_")

    df: pd.DataFrame = pd.concat(
        [reference, substrate],
        axis="columns",  # We want to join two tables so that the columns are the joining point (i.e left and right)
        join="inner",  # Take the intersection - only rows which have indexes present in both left and right tables will be passed through
    )

    df["X_Delta"] = df["Substrate_X_Displacement"] - df["Reference_X_Displacement"]
    df["Y_Delta"] = df["Substrate_Y_Displacement"] - df["Reference_Y_Displacement"]

    return df


def main():
    parser = argparse.ArgumentParser(
        description="""
    Given a list of directories this program will, for each directory:
    - Read substrate*.csv and reference*.csv

    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("folder", type=Path, nargs="+")
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
