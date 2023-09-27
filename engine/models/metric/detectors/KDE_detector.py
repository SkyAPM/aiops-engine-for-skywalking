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
from scipy.stats import gaussian_kde
from ..base import BaseDetector


class KDEDetector(BaseDetector):
    def __init__(self, threshold: int = 0.01, **kwargs):
        """Univariate KDE model. Suit for Latency or other metrics with multimodal distributions.
        Args:
            threshold (float, optional): Threshold for the probability of anomalies, a small float value. Defaults to 1e-4.
            window_len (int, optional): Length of the window for reference. Defaults to 200.
        """
        super().__init__(data_type="univariate", **kwargs)
        self.threshold = threshold

    def fit(self, X: np.ndarray, timestamp: int = None):
        self.window.append(X[0])

        return self

    def score(self, X: np.ndarray, timestamp: int = None) -> float:
        kde = gaussian_kde(self.window)
        density = kde.evaluate(X[0])

        return 1.0 if density < self.threshold else 0.0
