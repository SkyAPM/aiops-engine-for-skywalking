from abc import ABC, abstractmethod
from typing import Union
from datetime import datetime
from dateutil.parser import parse
import numpy as np

class BaseDetector(ABC):
    """Abstract class for Detector, supporting for customize detector."""

    def __init__(self):
        """Initialization BaseDetector"""
        self.data_type = "multivariate"
        self.index = -1
        self.window_len = 100

    def _check(self, timestamp: str, X: Union[float, int]) -> bool:
        """Check whether the detector can handle the data."""

        assert type(X) in [
            float,
            int
        ], "Please input X with float or int type."
        assert type(timestamp)

        self.index += 1

    @abstractmethod
    def fit(self, X: float):

        return NotImplementedError

    @abstractmethod
    def score(self, X: float) -> float:

        return NotImplementedError

    def fit_score(self, timestamp: str, X: Union[float, int]) -> float:
        """Fit once observation and return the anomaly score.

        Args:
            timestamp (str): The timestamp of the observation.
            X (Union[float, int]): The value of the observation.

        Returns:
            float: Anomaly score.
        """

        self._check(timestamp, X)
        if self.index < self.window_len:
            self.fit(X)
            return None

        score = self.fit(X).score(X)

        return float(score)
