import logging
import argparse
from pathlib import Path
from typing import Optional
import pandas as pd
import string

logger = logging.getLogger(__name__)


def read_displacement_csv(path: Path):
    """Reads in a CSV, returning a dataframe with:
    - (Index)
    - Frame
    - X_Position
    - Y_Position

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
            "E": "X_Position",
            "F": "Y_Position",
        },
        inplace=True,
    )

    # Pandas interpreted this as a float. Fix that now
    df["Frame"] = df["Frame"].astype(int)

    df.drop(
        # We've pulled out all of the columns we want, so drop the ones that we don't need (which have single-character names)
        labels=[col for col in df.columns if len(col) == 1],
        axis="columns",
        inplace=True,
    )

    logger.info(f"Loaded csv from {path.as_posix()} ({len(df)} rows)")

    return df


def merge_and_displace_frames(
    substrate: pd.DataFrame,
    reference: pd.DataFrame,
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
    logger.info(
        f"Resampled to buckets of {duration_of_resampled_row} ({len(combined)} rows)"
    )

    combined["X_Delta"] = (
        combined["Substrate_X_Position"] - combined["Reference_X_Position"]
    )
    combined["Y_Delta"] = (
        combined["Substrate_Y_Position"] - combined["Reference_Y_Position"]
    )

    # Make our delta lines start at 0
    x_start = combined["X_Delta"].iloc[0]
    y_start = combined["Y_Delta"].iloc[0]

    combined["X_Delta"] = combined["X_Delta"] - x_start
    combined["Y_Delta"] = combined["Y_Delta"] - y_start

    return combined


def generate_normal_force_and_correct_for_load_positioning(
    df: pd.DataFrame,
    initial_x_displacement: float,
    substrate_tip_position: float,
    length_of_substrate: float,
    stiffness_constant_of_substrate: float,
    stiffness_constant_of_pipette: float,
    pipette_position_at_rest: Optional[float] = None,
):
    displaced_x_delta = df["X_Delta"] + initial_x_displacement
    bead_to_tip_displacement = (
        substrate_tip_position - df["Substrate_Y_Position"].iloc[0]
    )
    length_from_the_tip = length_of_substrate - bead_to_tip_displacement
    df["Corrected_Deflection"] = (
        0.5 * (displaced_x_delta * (3 * length_of_substrate - length_from_the_tip))
    ) / length_from_the_tip

    df["Normal_Force"] = df["Corrected_Deflection"] * stiffness_constant_of_substrate

    # TODO: statistically sound heuristic here!
    if pipette_position_at_rest is None:
        pipette_position_at_rest = df["Pipette_Y_Position"][
            : pd.Timedelta(3, "seconds")
        ].mean()

        logger.info(
            f"Guessing pipette position at rest based on first 3 seconds of measurement (got {pipette_position_at_rest})"
        )

    df["Pipette_Deflection"] = df["Pipette_Y_Position"] - pipette_position_at_rest

    df["Friction_Force"] = df["Pipette_Deflection"] * stiffness_constant_of_pipette

    df["Friction_Coefficient"] = df["Friction_Force"] / df["Normal_Force"]

    return df


def main():
    parser = argparse.ArgumentParser(
        description="""
    Given a list of directories this program will, for each directory:
    - Read substrate*.csv, reference*.csv and pipette*.csv
    - Convert them to timeseries, and concatenate
    - Resample
    - Do some basic analysis
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="""The name of the folder containing the three csvs, with names containing either "reference", "substrate" or "pipette" (one of each)""",
    )
    parser.add_argument(
        "-e",
        "--experiment-duration",
        type=float,
        help="Duration of this experiment, in seconds",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--resample-to",
        type=float,
        help="How many seconds each row should last for after resampling",
        required=True,
    )

    parser.add_argument("-x", "--initial-x-displacement", type=float, required=True)
    parser.add_argument("-t", "--substrate-tip-position", type=float, required=True)
    parser.add_argument("-L", "--substrate-length", type=float, required=True)
    parser.add_argument("-s", "--substrate-stiffness", type=float, required=True)
    parser.add_argument("-p", "--pipette-stiffness", type=float, required=True)
    parser.add_argument("-R", "--pipette-position-at-rest", type=float, required=True)
    parser.add_argument(
        "-o",
        "--output-file-name",
        type=str,
        default="processed.csv",
        help="The name of the file to save the results to. Defaults to `processed.csv`",
    )
    parser.add_argument(
        "-O",
        "--overwrite",
        default=False,
        action="store_true",
        help="If the output filename already exists, ovewrite it. Else, the program will raise an error",
    )
    parser.add_argument(
        "-j",
        "--json",
        default=False,
        action="store_true",
        help="Also save as a `processed.json` file, for loading into other programs (like python).",
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
    folder: Path = args.folder

    def glob_once(folder: Path, pattern: str):
        candidates = list(folder.glob(pattern))
        assert len(candidates) == 1, f"Found more than file for {pattern}: {candidates}"
        destination_path = candidates.pop()
        assert destination_path.is_file()
        logging.info(f"Using {destination_path.as_posix()}")
        return destination_path

    substrate_path = glob_once(folder, "*[sS]ubstrate*.csv")
    reference_path = glob_once(folder, "*[rR]eference*.csv")
    pipette_path = glob_once(folder, "*[pP]ipette*.csv")

    merged_and_displaced = merge_and_displace_frames(
        substrate=read_displacement_csv(substrate_path),
        reference=read_displacement_csv(reference_path),
        pipette=read_displacement_csv(pipette_path),
        experiment_duration=pd.Timedelta(
            value=args.experiment_duration, unit="seconds"
        ),
        duration_of_resampled_row=pd.Timedelta(value=args.resample_to, unit="seconds"),
    )

    result = generate_normal_force_and_correct_for_load_positioning(
        df=merged_and_displaced,
        initial_x_displacement=args.initial_x_displacement,
        substrate_tip_position=args.substrate_tip_position,
        length_of_substrate=args.substrate_length,
        stiffness_constant_of_substrate=args.substrate_stiffness,
        stiffness_constant_of_pipette=args.pipette_stiffness,
        pipette_position_at_rest=args.pipette_position_at_rest,
    )

    output_file = folder.joinpath(args.output_file_name)
    if output_file.exists():
        assert output_file.is_file()
        assert (
            args.overwrite
        ), f"About to write over existing file {output_file}, but `--overwrite` not specified"
        logger.warn(f"Overwriting file {output_file.as_posix()}")

    result.to_csv(output_file)

    if args.json:
        result.to_json(folder.joinpath("processed.json"))
