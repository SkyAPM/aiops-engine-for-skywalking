from collections import deque
import numpy as np
class AlertManager:
    def __init__(self, tolearance: int = 5, least_alert: int = 2) -> None:
        self.tolearance = tolearance
        self.least_alert = least_alert
        self.alert_cnt = 0
        self.non_alert_cnt = 0
        self.is_alerting = False
        self.filter = deque(maxlen=20)

    def get_alert(self, timestamp, X, score: float):
        if score is None:
            return None
        assert type(score) is float or type(score) is int, "Score must be float"
        assert 0 <= score <= 1, "Score must be between 0 and 1"

        if score == 1.0:
            if len(self.filter) > 4:
                filters = {idx:abs(X-i) for idx, i in enumerate(self.filter)}
                filters = dict(sorted(filters.items(), key= lambda x: x[1]))

                refs = np.array(self.filter)[np.array(list(filters.keys())[:10])]
                refs_mean = np.mean(refs)
                refs_std = np.std(refs)
                res_score = abs(X - refs_mean) / refs_std if refs_std !=0 else abs(X - refs_mean)
                if res_score < 2:
                    score = 0.5
            self.filter.append(X)

        if score == 1.0:
            self.alert_cnt += 1
            self.non_alert_cnt = 0
            if self.alert_cnt > self.least_alert:
                # Notification to alert
                # print('Alert Begin')
                self.is_alerting = True
            else:
                score = 0.0

        else:
            self.non_alert_cnt += 1
            if self.non_alert_cnt > self.tolearance:
                # Notification to alert
                # print('Alert End')
                self.alert_cnt = 0
                self.non_alert_cnt = 0
                self.is_alerting = False

            elif self.is_alerting:
                # This can be set for normal data to alerts.
                # score = 1.0
                score = score

        return score
