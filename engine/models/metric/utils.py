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


from typing import Union


class AlertManager:
    def __init__(self, tolearance: int = 5, least_alert: int = 2) -> None:
        self.tolearance = tolearance
        self.least_alert = least_alert
        self.alert_cnt = 0
        self.non_alert_cnt = 0
        self.is_alerting = False

    def get_alert(self, timestamp: str, data: Union[float, int], score: float):
        if score is None:
            return None
        assert type(score) is float or type(score) is int, 'Score must be float'
        assert 0 <= score <= 1, 'Score must be between 0 and 1'


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
