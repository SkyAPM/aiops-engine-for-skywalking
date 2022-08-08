class AlertManager:
    def __init__(self, tolearance: int = 5, least_alert: int = 2) -> None:
        self.tolearance = tolearance
        self.least_alert = least_alert
        self.alert_cnt = 0
        self.non_alert_cnt = 0
        self.is_alerting = False

    def get_alert(self, timestamp, score: float):
        if score is None:
            return None
        assert type(score) is float or type(score) is int, "Score must be float"
        assert 0 <= score <= 1, "Score must be between 0 and 1"

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
                score = 1.0

        return score
