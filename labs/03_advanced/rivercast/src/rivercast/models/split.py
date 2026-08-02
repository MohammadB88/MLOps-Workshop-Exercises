"""Temporal train/validation/test split (PLAN.md Phase 6).

Chronological, non-shuffled: training is the oldest interval, validation the
following interval, test the newest untouched interval. This is the one
place preprocessing "fit" boundaries are decided — any scaler/encoder fit
downstream must be fit on ``train`` only (rule: fit preprocessing only on the
training window) and applied unchanged to ``validation``/``test``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TemporalSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame

    def __post_init__(self) -> None:
        for name, part in (
            ("train", self.train),
            ("validation", self.validation),
            ("test", self.test),
        ):
            if not part.index.is_monotonic_increasing:
                raise ValueError(f"{name} split is not sorted by issue time")
        if (
            len(self.train)
            and len(self.validation)
            and self.train.index.max() >= self.validation.index.min()
        ):
            raise ValueError("train interval must end strictly before validation begins")
        if (
            len(self.validation)
            and len(self.test)
            and self.validation.index.max() >= self.test.index.min()
        ):
            raise ValueError("validation interval must end strictly before test begins")


def temporal_split(
    dataset: pd.DataFrame,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
) -> TemporalSplit:
    """Split a time-indexed, already-sorted dataset chronologically.

    ``train_fraction + validation_fraction`` must be < 1; the remainder is
    the test interval. No shuffling, no random state — order is time itself.
    """
    if not (0 < train_fraction < 1) or not (0 < validation_fraction < 1):
        raise ValueError("train_fraction and validation_fraction must each be in (0, 1)")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train_fraction + validation_fraction must be < 1 (test needs a share)")
    if not dataset.index.is_monotonic_increasing:
        raise ValueError("dataset must be sorted by issue time before splitting")

    n = len(dataset)
    train_end = int(n * train_fraction)
    validation_end = train_end + int(n * validation_fraction)
    return TemporalSplit(
        train=dataset.iloc[:train_end],
        validation=dataset.iloc[train_end:validation_end],
        test=dataset.iloc[validation_end:],
    )
