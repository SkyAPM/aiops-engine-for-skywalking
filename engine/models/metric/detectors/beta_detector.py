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

from engine.models.metric.base.detector import BaseDetector


class BetaDetector(BaseDetector):
    def __init__(self, threshold: int = 1e-4, **kwargs):
        """Univariate beta model. The data is scaled to [0, 1] before fitting. Suit for Percent metrics.
        Args:
            threshold (float, optional): Threshold for the probability of anomalies, a small float value. Defaults to 1e-4.
            window_len (int, optional): Length of the window for reference. Defaults to 200.
        """
        super().__init__(data_type='univariate', **kwargs)
        self.threshold = threshold

    def fit(self, X: np.ndarray, timestamp: int = None):
        self.window.append(X[0] / 100)

        return self

    def score(self, X: np.ndarray, timestamp: int = None) -> float:
        alpha_hat, beta_hat, _, _ = beta.fit(self.window, floc=0, fscale=1)

        density = beta.pdf(X[0] / 100, alpha_hat, beta_hat)

        return 1.0 if density < self.threshold else 0.0
