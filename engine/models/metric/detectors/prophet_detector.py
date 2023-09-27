
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
from prophet import Prophet
import pandas as pd
from ..base import BaseDetector

class ProphetDetector(BaseDetector):
    def __init__(self, **kwargs):
        """Univariate prophet model. Suit for Traffic or other metrics with period and trend that can forecast.
        Args:
            threshold (float, optional): Threshold for the probability of anomalies, a small float value. Defaults to 1e-4.
            window_len (int, optional): Length of the window for reference. Defaults to 200.
        """
        super().__init__(data_type="univariate", **kwargs)

    def fit(self, X: np.ndarray, timestamp: int = None):
        self.window.append({'ds': pd.to_datetime(timestamp, unit='s'), 'y': X[0]})

        return self

    def score(self, X: np.ndarray, timestamp: int = None) -> float:
        df = pd.DataFrame.from_records(self.window)
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=1)
        forecast = model.predict(future)

        predicted_value = forecast['yhat'].iloc[-1]
        residual = abs(predicted_value - X[0])
        print(residual, X[0])

        return 1.0 if residual / X[0] > 1.0 else 0.0

