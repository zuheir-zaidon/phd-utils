import phd_utils.resample as subject

import pytest
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def test_resample():
    fps500 = (
        pd.timedelta_range(start="0s", end="0.1s", periods=50, name="instant")
        .to_frame(index=False)
        .set_index("instant")
    )

    fps600 = (
        pd.timedelta_range(start="0s", end="0.1s", periods=60, name="instant")
        .to_frame(index=False)
        .set_index("instant")
    )

    fps500["Reference"] = range(1, 51)
    fps600["Substrate"] = range(1, 61)

    logger.debug(fps500)
    logger.debug(fps600)

    ##########
    # METHOD 1
    ##########
    # Merge
    df = pd.concat([fps500, fps600]).sort_index()

    # Optionally interpolate at this step
    df = df.interpolate(
        method="linear"
    )  # Could also be "nearest" etc. See https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.interpolate.html

    # Optionally resample to a fixed interval.
    # May be worth avoiding if future steps are time-zone aware
    interval = pd.Timedelta(value=10, unit="milliseconds")
    df = df.resample(interval).mean()  # Could also be min, max, sum etc
    logger.debug(df)
