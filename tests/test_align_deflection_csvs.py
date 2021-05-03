import phd_utils.align_deflection_csvs as subject
import pytest
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def reference_csv(assets: Path):
    return assets / "reference.csv"


@pytest.fixture
def substrate_csv(assets: Path):
    return assets / "substrate.csv"


@pytest.fixture
def pipette_csv(assets: Path):
    return assets / "pipette.csv"


def test_read_csv(reference_csv: Path):
    df = subject.read_displacement_csv(reference_csv)
    logger.debug(df)
    logger.debug(df.columns)


def test_calculate_displacment():
    reference = pd.DataFrame.from_dict(
        {
            "Frame": [1, 2, 3],
            "X_Displacement": [100, 200, 300],
            "Y_Displacement": [1000, 2000, 3000],
        }
    ).set_index("Frame")

    substrate = pd.DataFrame.from_dict(
        {
            "Frame": [2, 3, 4],
            "X_Displacement": [202, 303, 404],
            "Y_Displacement": [2020, 3030, 4040],
        }
    ).set_index("Frame")

    expected_df = pd.DataFrame.from_dict(
        {
            "Frame": [2, 3],  # Only frames common to the two
            "Reference_X_Displacement": [200, 300],
            "Reference_Y_Displacement": [2000, 3000],
            "Substrate_X_Displacement": [202, 303],
            "Substrate_Y_Displacement": [2020, 3030],
            "X_Delta": [2, 3],
            "Y_Delta": [20, 30],
        }
    ).set_index("Frame")

    df = subject.calculate_displacement(reference=reference, substrate=substrate)

    logger.debug(df)

    assert df.equals(expected_df)
