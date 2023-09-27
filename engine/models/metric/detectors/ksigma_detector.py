#  Copyright 2023 SkyAPM org
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

import numpy as np
from scipy.stats import beta
from ..base import BaseDetector


class KSigmaDetector(BaseDetector):
    def __init__(self, k: int = 3, **kwargs):
        """Univariate gaussian model. 
        Args:
            k (int, optional): K times the standard deviation (sigma) to consider outliter. Defaults to 3.
            window_len (int, optional): Length of the window for reference. Defaults to 200.
        """
        super().__init__(data_type="univariate", **kwargs)

    def fit(self, X: np.ndarray, timestamp: int = None):
        self.window.append(X[0])

        return self

    def score(self, X: np.ndarray, timestamp: int = None) -> float:
        mean = np.mean(self.window)
        std = np.std(self.window)

        return 1.0 if abs(mean -  X[0]) > std * self.k else 0.0
