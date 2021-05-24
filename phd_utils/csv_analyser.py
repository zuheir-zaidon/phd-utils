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
    pipette: pd.DataFrame,
    experiment_duration: pd.Timedelta,
    duration_of_resampled_row: pd.Timedelta,
):
    reference = reference.add_prefix("Reference_")
    substrate = substrate.add_prefix("Substrate_")
    pipette = pipette.add_prefix("Pipette_")

    # Convert from frame numbers to the actual time through the experiment
    for df, name in [
        (reference, "Reference"),
        (substrate, "Substrate"),
        (pipette, "Pipette"),
    ]:
        df: pd.DataFrame
        name: str
        number_of_frames = df[f"{name}_Frame"].max()
        instant = df[f"{name}_Frame"] / number_of_frames * experiment_duration
        df[f"{name}_Instant"] = instant
        df.set_index(f"{name}_Instant", inplace=True)

    combined = pd.concat(
        (reference, substrate, pipette),
        axis="columns",  # We want to join two tables so that the columns are the joining point (i.e left and right)
    )

    # In order to compare results between experiments, we must now resample them (so that each row has a common `Instant`)
    # This is a lossy operation. We choose to take the mean
    combined: pd.DataFrame = combined.resample(rule=duration_of_resampled_row).mean()
    # Frame numbers are no longer valid
    combined.drop(
        columns=[col for col in combined.columns if col.endswith("Frame")],
        inplace=True,
    )

    combined["X_Delta"] = (
        combined["Substrate_X_Displacement"] - combined["Reference_X_Displacement"]
    )
    combined["Y_Delta"] = (
        combined["Substrate_Y_Displacement"] - combined["Reference_Y_Displacement"]
    )

    # Make our delta lines start at 0
    x_start = combined["X_Delta"].iloc[0]
    y_start = combined["Y_Delta"].iloc[0]

    combined["X_Delta"] = combined["X_Delta"] - x_start
    combined["Y_Delta"] = combined["Y_Delta"] - y_start

    return combined


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
