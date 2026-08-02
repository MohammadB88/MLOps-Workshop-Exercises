"""Temporal split tests: chronological ordering, no leakage across boundaries."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from rivercast.models.split import TemporalSplit, temporal_split

START = datetime(2024, 8, 1, tzinfo=UTC)


def _frame(n: int) -> pd.DataFrame:
    index = pd.DatetimeIndex([START + timedelta(hours=i) for i in range(n)], name="issue_time_utc")
    return pd.DataFrame({"value": range(n)}, index=index)


def test_split_sizes_and_order() -> None:
    dataset = _frame(100)
    split = temporal_split(dataset, train_fraction=0.7, validation_fraction=0.15)
    assert len(split.train) == 70
    assert len(split.validation) == 15
    assert len(split.test) == 15
    assert split.train.index.max() < split.validation.index.min()
    assert split.validation.index.max() < split.test.index.min()


def test_split_covers_every_row_exactly_once() -> None:
    dataset = _frame(50)
    split = temporal_split(dataset)
    combined = pd.concat([split.train, split.validation, split.test])
    assert len(combined) == len(dataset)
    assert combined.index.equals(dataset.index)


def test_unsorted_dataset_rejected() -> None:
    dataset = _frame(10).iloc[::-1]
    with pytest.raises(ValueError, match="sorted by issue time"):
        temporal_split(dataset)


def test_fractions_must_leave_room_for_test() -> None:
    with pytest.raises(ValueError, match="< 1"):
        temporal_split(_frame(10), train_fraction=0.8, validation_fraction=0.3)


@pytest.mark.parametrize("bad_fraction", [0.0, 1.0, -0.1, 1.5])
def test_fractions_must_be_in_open_unit_interval(bad_fraction: float) -> None:
    with pytest.raises(ValueError, match=r"in \(0, 1\)"):
        temporal_split(_frame(10), train_fraction=bad_fraction)


def test_temporal_split_post_init_rejects_overlapping_intervals() -> None:
    frame = _frame(10)
    with pytest.raises(ValueError, match="train interval must end"):
        TemporalSplit(train=frame.iloc[0:5], validation=frame.iloc[3:8], test=frame.iloc[8:10])
