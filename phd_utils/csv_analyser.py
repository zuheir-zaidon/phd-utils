import logging
import argparse
from pathlib import Path
from typing import Optional
from numpy import cos
import pandas as pd
import string
import datetime


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
        index_col=False,
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
        # pd.Timedelta -> seconds
        df["Instant"] = instant
        df.set_index("Instant", inplace=True)

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
    initial_substrate_tip_position: float,
    length_of_substrate: float,
    stiffness_constant_of_substrate: float,
    stiffness_constant_of_pipette: float,
    reverse_sliding_direction: bool,
    angle_alpha: float,
    angle_beta: float,
    substrate_tip_velocity: float, # micrometres per second
    flexural_rigidity: float,
    duration_subtrate_tip_is_stationary_for: pd.Timedelta = pd.Timedelta(5, "seconds")
    # pipette_position_at_rest: Optional[float] = None,
):
    # Pretend we're at a constant velocity for the whole thing (in micrometers per second)
    df["Substrate_Tip_Position"] = df.index.total_seconds() * substrate_tip_velocity
    # Now shift our line to the right, because we're stationary for the first n seconds
    df["Substrate_Tip_Position"] = df["Substrate_Tip_Position"].shift(freq=duration_subtrate_tip_is_stationary_for)
    # Fill in the missing values (add a flat section to the line)
    df["Substrate_Tip_Position"].fillna(0)
    # Translate up the y axis
    df["Substrate_Tip_Position"] = df["Substrate_Tip_Position"] + initial_substrate_tip_position

    displaced_x_delta = df["X_Delta"] / cos(angle_beta) + initial_x_displacement
    bead_to_tip_displacement = df["Pipette_Y_Position"] - df["Substrate_Tip_Position"]
    
    length_from_the_tip = length_of_substrate - bead_to_tip_displacement
    df["Corrected_Deflection"] = (
        displaced_x_delta
        * stiffness_constant_of_substrate
        * length_from_the_tip
        * length_from_the_tip
        * (3 * length_of_substrate - length_from_the_tip)
        / (6 * flexural_rigidity * 10 ** 16)
    )
    df["Normal_Force"] = df["Corrected_Deflection"] * stiffness_constant_of_substrate

    if angle_alpha > 0:
        holder = cos(angle_alpha)
    else:
        holder = 1
        
    if reverse_sliding_direction is True:  # user said -d
        df["Pipette_Deflection"] = (
            df["Pipette_Y_Position"] * holder - df["Pipette_Y_Position"].iloc[0]
        )
    else:  # user didn't say -d
        df["Pipette_Deflection"] = (
            df["Pipette_Y_Position"].iloc[0] - df["Pipette_Y_Position"] * holder
        )

    df["Friction_Force"] = (
        df["Pipette_Deflection"] / cos(angle_beta) * stiffness_constant_of_pipette
    )

    df["Friction_Coefficient"] = df["Friction_Force"] / df["Normal_Force"]

    return df


def main():
    parser = argparse.ArgumentParser(
        description="""
    Given a string, this program will
    - Read substrate*.csv, reference*.csv and pipette*.csv, where each filename contains that string
    - Convert them to timeseries, and concatenate
    - Resample
    - Do some basic analysis
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--filename-contains",
        type=str,
        help="""Look for the substrate, reference and pipette csvs which have their filenames containing this number""",
    )
    parser.add_argument(
        "-f",
        "--folder",
        type=Path,
        default=Path.cwd(),
        help="The folder to look in. Defaults to the current working directory",
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
    parser.add_argument("-k", "--substrate-stiffness", type=float, required=True)
    parser.add_argument("-j", "--pipette-stiffness", type=float, required=True)
    # parser.add_argument("-R", "--pipette-position-at-rest", type=float, default=None, required=False)
    parser.add_argument("-a", "--angle-alpha", type=float, default=None, required=False)
    parser.add_argument("-b", "--angle-beta", type=float, default=None, required=False)
    parser.add_argument("-s", "--speed", type=float, default=None, required=False)
    parser.add_argument(
        "-fr", "--flexural-rigidity", type=float, default=None, required=False
    )
    parser.add_argument(
        "-d", "--reverse-sliding-direction", default=False, action="store_true"
    )
    parser.add_argument(
        "-O",
        "--overwrite",
        default=False,
        action="store_true",
        help="If the output filename already exists, ovewrite it. Else, the program will raise an error",
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

    analyse_csv(
        filename=args.filename_contains,
        folder=args.folder,
        experiment_duration=args.experiment_duration,
        resample_to=args.resample_to,
        initial_x_displacement=args.initial_x_displacement,
        substrate_tip_position=args.substrate_tip_position,
        length_of_substrate=args.substrate_length,
        stiffness_constant_of_substrate=args.substrate_stiffness,
        stiffness_constant_of_pipette=args.pipette_stiffness,
        reverse_sliding_direction=args.reverse_sliding_direction,
        angle_alpha=args.angle_alpha,
        angle_beta=args.angle_beta,
        speed=args.speed,
        flexural_rigidity=args.flexural_rigidity,
        # pipette_position_at_rest=args.pipette_position_at_rest,
        overwrite=args.overwrite,
    )


def glob_once(folder: Path, pattern: str):
    candidates = list(folder.glob(pattern))
    assert len(candidates) == 1, f"Found more than file for {pattern}: {candidates}"
    destination_path = candidates.pop()
    assert destination_path.is_file()
    logging.info(f"Using {destination_path.as_posix()}")
    return destination_path


def analyse_csv(
    filename: str,
    folder: Path,  # yes
    experiment_duration: float,  # yes
    resample_to: float,
    initial_x_displacement: float,  # yes
    substrate_tip_position: float,  # yes
    length_of_substrate: float,
    stiffness_constant_of_substrate: float,
    stiffness_constant_of_pipette: float,
    reverse_sliding_direction: bool,  # yes
    angle_alpha: float,
    angle_beta: float,
    speed: float,
    flexural_rigidity: float,
    # pipette_position_at_rest: Optional[float],
    overwrite: bool,
):
    """This function does the entire analysis for one experiment"""

    substrate_path = glob_once(folder, f"substrate_{filename}.csv")
    reference_path = glob_once(folder, f"reference_{filename}.csv")
    pipette_path = glob_once(folder, f"pipette_{filename}.csv")

    merged_and_displaced = merge_and_displace_frames(
        substrate=read_displacement_csv(substrate_path),
        reference=read_displacement_csv(reference_path),
        pipette=read_displacement_csv(pipette_path),
        experiment_duration=pd.Timedelta(value=experiment_duration, unit="seconds"),
        duration_of_resampled_row=pd.Timedelta(value=resample_to, unit="seconds"),
    )

    result = generate_normal_force_and_correct_for_load_positioning(
        df=merged_and_displaced,
        initial_x_displacement=initial_x_displacement,
        initial_substrate_tip_position=substrate_tip_position,
        length_of_substrate=length_of_substrate,
        stiffness_constant_of_substrate=stiffness_constant_of_substrate,
        stiffness_constant_of_pipette=stiffness_constant_of_pipette,
        reverse_sliding_direction=reverse_sliding_direction,
        angle_alpha=angle_alpha,
        angle_beta=angle_beta,
        substrate_tip_velocity=speed,
        flexural_rigidity=flexural_rigidity,
        # pipette_position_at_rest=pipette_position_at_rest,
    )

    output_file = folder.joinpath(f"processed_{filename}.csv")
    if output_file.exists():
        assert output_file.is_file()
        assert (
            overwrite is True
        ), f"About to write over existing file {output_file}, but `--overwrite` not specified"
        logger.warn(f"Overwriting file {output_file.as_posix()}")

    result.to_csv(output_file)
