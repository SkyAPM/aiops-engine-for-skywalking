import sys

sys.path.append("../../")
from engine.models.metric.utils import AlertManager


def test_alert():

    manager = AlertManager(tolearance=5, least_alert=2)

    for i in [0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1]:
        score = manager.get_alert(score=i)
        print(score)
