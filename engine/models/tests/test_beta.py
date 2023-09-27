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


from datetime import datetime
import json
import os
import sys
from time import perf_counter
import numpy as np

import pandas as pd

from engine.models.metric.detectors import BetaDetector
from engine.models.tests.evaluate.numenta_aware_metrics import NumentaAwareMetircs
from engine.models.tests.evaluate.point_aware_metrics import PointAwareMetircs
from engine.models.tests.evaluate.series_aware_metrics import SeriesAwareMetircs

sys.path.append("../../")


def test_beta_detector_uni_dataset():
    base_path = "experiments/metric/data"
    datasets_dir = "realAWSCloudwatch"
    dataset_threshold = {
        "ec2_cpu_utilization_825cc2.csv": 1e-25,
        "ec2_cpu_utilization_5f5533.csv": 0.15,
        "ec2_cpu_utilization_ac20cd.csv": 1e-50,
        "rds_cpu_utilization_cc0c53.csv": 1e-30,
        "rds_cpu_utilization_e47b3b.csv": 1e-20,
    }
    for dataset, threshold in dataset_threshold.items():
        file_path = os.path.join(base_path, datasets_dir, dataset)
        df = pd.read_csv(file_path)
        detector = BetaDetector(window_len=2 * 288, threshold=threshold)

        scores = []
        start_time = perf_counter()
        for _, row in df.iterrows():
            timestamp = row.timestamp
            if type(timestamp) == str:
                timestamp = int(datetime.strptime(row.timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
            data = np.array([row.value])
            score = detector.fit_score(X=data, timestamp=timestamp)
            assert score is None or 0 <= score <= 1
            scores.append(score)

        time = perf_counter() - start_time

        labels = json.load(open(os.path.join(base_path, "labels/combined_labels.json")))
        key = datasets_dir + "/" + dataset
        label_timestamp = labels[key]
        df["label"] = 0
        df.loc[df["timestamp"].isin(label_timestamp), "label"] = 1
        label = df["label"].to_numpy().squeeze()

        print(f"Dataset: {dataset}")
        print(f"Time: {time:.2f}s")
        for metric in [
            PointAwareMetircs(),
            SeriesAwareMetircs(),
            NumentaAwareMetircs(),
        ]:
            precision, recall, F1 = metric.evaluate(label, scores)
            print(metric.__class__.__name__)
            print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {F1:.2f}")
