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


from datetime import datetime
import sys
import numpy as np

import pandas as pd

from engine.models.metric.detectors import SpotDetector

sys.path.append('../../')


def test_detector_uni_dataset():
    df = pd.read_csv(
        'experiments/metric/data/univarate_dataset.csv'
    )
    detector = SpotDetector()

    for _, row in df.iterrows():
        timestamp = row.timestamp
        if isinstance(timestamp, str):
            timestamp = int(datetime.strptime(row.timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
        data = np.array([row.value])
        score = detector.fit_score(X=data, timestamp=timestamp)
        assert score is None or 0 <= score <= 1
