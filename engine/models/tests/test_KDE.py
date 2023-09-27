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

from engine.models.metric.detectors import KDEDetector
from engine.models.tests.evaluate.numenta_aware_metrics import NumentaAwareMetircs
from engine.models.tests.evaluate.point_aware_metrics import PointAwareMetircs
from engine.models.tests.evaluate.series_aware_metrics import SeriesAwareMetircs

sys.path.append("../../")


def test_KDE_detector_uni_dataset():
    base_path = "experiments/metric/data"
    datasets_dir = "realAWSCloudwatch"
    dataset_threshold = {
        "ec2_disk_write_bytes_1ef3de.csv": 1e-20,
        "ec2_disk_write_bytes_c0d644.csv": 1e-17,
        "ec2_network_in_5abac7.csv": 1e-12,
        "ec2_network_in_257a54.csv": 1e-50
    }
    for dataset, threshold in dataset_threshold.items():
        file_path = os.path.join(base_path, datasets_dir, dataset)
        df = pd.read_csv(file_path)
        detector = KDEDetector(window_len=5 * 288, threshold=threshold)

        scores = []
        start_time = perf_counter()
        for _, row in df.iterrows():
            timestamp = row.timestamp
            if isinstance(timestamp, str):
                timestamp = int(
                    datetime.strptime(row.timestamp, "%Y-%m-%d %H:%M:%S").timestamp()
                )
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

        print(f"\nDataset: {dataset}")
        print(f"Time: {time:.2f}s")
        for metric in [
            PointAwareMetircs(),
            SeriesAwareMetircs(),
            NumentaAwareMetircs(),
        ]:
            precision, recall, F1 = metric.evaluate(label, scores)
            print(metric.__class__.__name__)
            print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {F1:.2f}")
