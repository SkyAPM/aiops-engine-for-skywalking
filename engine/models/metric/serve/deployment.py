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

import ray


@ray.remote(num_cpus=1)
class RayMetricConsumer(object):
    def __init__(self, detector) -> None:
        self.detector = detector

    def run(self, timestamp: str, data: float) -> float:
        score = self.detector.fit_score(timestamp=timestamp, data=float(data))
        return score


if __name__ == "__main__":

    from engine.models.metric.detectors import SpotDetector
    import pandas as pd

    df = pd.read_csv(
        "experiments/metric/data/univarate_dataset.csv", index_col="timestamp"
    )

    # This for loop can be replaced by a MQ
    for index, row in df.iterrows():
        timestamp = index
        data = row.value

        # Here we setup multi-consumer according to unique name
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
