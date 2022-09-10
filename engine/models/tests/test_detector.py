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

import sys

import pandas as pd

from engine.models.metric.detectors import SpotDetector

sys.path.append('../../')


def test_detector_uni_dataset():
    df = pd.read_csv(
        'example/metric/data/univarate_dataset.csv', index_col='timestamp'
    )
    detector = SpotDetector()

    for index, row in df.iterrows():
        timestamp = index
        X = row.value
        score = detector.fit_score(timestamp=timestamp, X=float(X))
        assert score is None or 0 <= score <= 1
