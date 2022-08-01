import sys

sys.path.append("../../")
import pandas as pd
from engine.models.metric.detector import SpotDetector


def test_detector_uni_dataset():
    df = pd.read_csv(
        "example/metric/data/univarate_dataset.csv", index_col="timestamp"
    )
    detector = SpotDetector()

    for index, row in df.iterrows():
        timestamp = index
        X = row.value
        score = detector.fit_score(timestamp=timestamp, X=float(X))
        assert score is None or 0 <= score <= 1
