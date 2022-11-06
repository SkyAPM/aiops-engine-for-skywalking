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


import sys

import pandas as pd

from engine.models.metric.detectors import SpotDetector
from engine.models.metric.serve.deployment import RayMetricConsumer
import ray

sys.path.append("../../")


def test_detector_uni_dataset():
    df = pd.read_csv(
        "experiments/metric/data/univarate_dataset.csv", index_col="timestamp"
    )
    detector = SpotDetector.remote()

    for index, row in df.iterrows():
        timestamp = index
        data = row.value

        score = ray.get(
            detector.fit_score.remote(timestamp=timestamp, data=float(data))
        )
        assert score is None or 0 <= score <= 1


def test_multi_detector_uni_dataset():
    df = pd.read_csv(
        "experiments/metric/data/univarate_dataset.csv", index_col="timestamp"
    )

    for index, row in df.iterrows():
        timestamp = index
        data = row.value

        detector = RayMetricConsumer.options(
            name="cpu.load", lifetime="detached", get_if_exists=True
        ).remote(SpotDetector())

        score1 = ray.get(
            detector.run.remote(timestamp=timestamp, data=float(data))
        )

        detector = RayMetricConsumer.options(
            name="mem.load", lifetime="detached", get_if_exists=True
        ).remote(SpotDetector())
        score2 = ray.get(
            detector.run.remote(timestamp=timestamp, data=float(data))
        )

        assert score1 == score2
