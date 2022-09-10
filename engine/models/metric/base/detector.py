#  Copyright 2022 SkyAPM org
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from abc import ABC, abstractmethod
from typing import Union


class BaseDetector(ABC):
    """Abstract class for Detector, supporting for customize detectors."""

    def __init__(self):
        """Initialization BaseDetector"""
        self.data_type = 'multivariate'
        self.index = -1
        self.window_len = 100

    def _check(self, timestamp: str, X: Union[float, int]) -> bool:
        """Check whether the detectors can handle the data."""

        assert type(X) in [
            float,
            int
        ], 'Please input X with float or int type.'
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
