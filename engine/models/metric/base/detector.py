# Copyright 2022 SkyAPM org
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from abc import ABC, abstractmethod
from collections import deque
from typing import Union, Literal


class BaseDetector(ABC):
    """Abstract class for Detector, supporting for customize detectors."""

    def __init__(self, window_len: int = 200, data_type: Literal['univariate', 'multivariate'] = 'univariate'):
        """Initialization BaseDetector

        Args:
            window_len (int, optional): Window length for observations. Defaults to 200.
            data_type (Literal['univariate', 'multivariate'], optional): Data type. Defaults to 'univariate'.
        """
        self.data_type = data_type
        self.index = -1
        self.window_len = window_len
        self.window = deque(maxlen=self.window_len)

    def _check(self, timestamp: str, data: Union[float, int]) -> bool:
        """Check whether the detectors can handle the data."""

        assert type(data) in [float, int], 'Please input data with float or int type.'
        assert type(timestamp)

        self.index += 1

    @abstractmethod
    def fit(self, data: Union[float, int]):
        return NotImplementedError

    @abstractmethod
    def score(self, data: Union[float, int]) -> float:
        return NotImplementedError

    def fit_score(self, timestamp: str, data: Union[float, int]) -> float:
        """Fit once observation and return the anomaly score.

        Args:
            timestamp (str): The timestamp of the observation.
            data (Union[float, int]): The value of the observation.

        Returns:
            float: Anomaly score.
        """

        self._check(timestamp, data)
        if self.index < self.window_len:
            self.fit(data)
            return None

        score = self.fit(data).score(data)

        return float(score)
