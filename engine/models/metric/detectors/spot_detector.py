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


import heapq
from collections import deque
from math import log
from typing import Union
import numpy as np
from scipy.optimize import minimize

from ..base import BaseDetector

np.seterr(divide='ignore', invalid='ignore')


class SpotDetector(BaseDetector):
    def __init__(
        self,
        prob: float = 1e-4,
        back_mean_len: int = 20,
        num_threshold_up: int = 20,
        num_threshold_down: int = 20,
        deviance_ratio: float = 0.01,
        **kwargs
    ):
        """Univariate Spot model.
        Args:
            prob (float, optional): Threshold for the probability of anomalies, a small float value. Defaults to 1e-4.
            back_mean_len (int, optional): The length of backward window to calculate the first-order difference. Defaults to 20.
            num_threshold_up (int, optional): Number of peaks over upper threshold to estimate distribution. Defaults to 20.
            num_threshold_down (int, optional): Number of peaks over lower threshold to estimate distribution. Defaults to 20.
            deviance_ratio (float, optional): Deviance ratio aginest the absolute value of data, which is useful when the value is very large and deviances are small. Defaults to 0.01.
            window_len (int, optional): Length of the window for reference. Defaults to 200.
        """

        super().__init__(**kwargs)

        self.prob = prob
        self.deviance_ratio = deviance_ratio
        self.back_mean_len = back_mean_len
        self.back_mean_window = deque(maxlen=self.back_mean_len)
        assert (
            self.window_len > 100
        ), 'window_len is too small, default value is 200'

        self.num_threshold = {
            'up': num_threshold_up,
            'down': num_threshold_down,
        }

        nonedict = {'up': None, 'down': None}

        self.extreme_quantile = dict.copy(nonedict)
        self.init_threshold = dict.copy(nonedict)
        self.peaks = dict.copy(nonedict)
        self.history_peaks = {'up': [], 'down': []}
        # self.peaks = {'up':deque(maxlen=20),'down':deque(maxlen=20)}
        self.gamma = dict.copy(nonedict)
        self.sigma = dict.copy(nonedict)
        self.normal_X = None

        # self.thup = []
        # self.thdown = []

    def _grimshaw(self, side, epsilon=1e-8, n_points=10):
        def u(s):
            return 1 + np.log(s).mean()

        def v(s):
            return np.mean(1 / s)

        def w(y, t):
            s = 1 + t * y
            us = u(s)
            vs = v(s)
            return us * vs - 1

        def jac_w(y, t):
            s = 1 + t * y
            us = u(s)
            vs = v(s)
            jac_us = np.divide(
                1, t, out=np.array(1 / epsilon), where=t != 0
            ) * (1 - vs)
            jac_vs = np.divide(
                1, t, out=np.array(1 / epsilon), where=t != 0
            ) * (-vs + np.mean(1 / s**2))
            return us * jac_vs + vs * jac_us

        self.peaks[side][self.peaks[side] == 0] = epsilon
        y_min = self.peaks[side].min()
        y_max = self.peaks[side].max()
        y_mean = self.peaks[side].mean()

        a = np.divide(-1, y_max, out=np.array(-epsilon), where=y_max != 0)
        if abs(a) < 2 * epsilon:
            epsilon = abs(a) / n_points

        # a = a + epsilon
        b = 2 * np.divide(
            (y_mean - y_min),
            (y_mean * y_min),
            out=np.array((y_mean - y_min) / epsilon - epsilon),
            where=(y_mean * y_min) != 0,
        )
        c = 2 * np.divide(
            y_mean - y_min,
            y_min**2,
            out=np.array((y_mean - y_min) / epsilon + epsilon),
            where=y_min != 0,
        )

        d = a + epsilon
        e = -epsilon

        left_zeros = self._roots_finder(
            lambda t: w(self.peaks[side], t),
            lambda t: jac_w(self.peaks[side], t),
            (d, e) if d < e else (e, d),
            n_points,
            'regular',
        )

        right_zeros = self._roots_finder(
            lambda t: w(self.peaks[side], t),
            lambda t: jac_w(self.peaks[side], t),
            (b, c) if b < c else (c, b),
            n_points,
            'regular',
        )

        # all the possible roots
        zeros = np.concatenate((left_zeros, right_zeros))

        # 0 is always a solution so we initialize with it
        gamma_best = 0
        sigma_best = y_mean
        ll_best = self._log_likelihood(self.peaks[side], gamma_best, sigma_best)

        # we look for better candidates
        for z in zeros:
            gamma = u(1 + z * self.peaks[side]) - 1
            sigma = np.divide(
                gamma, z, out=np.array(gamma / epsilon), where=z != 0
            )
            ll = self._log_likelihood(self.peaks[side], gamma, sigma)
            if ll > ll_best:
                gamma_best = gamma
                sigma_best = sigma
                ll_best = ll

        return gamma_best, sigma_best, ll_best

    def _roots_finder(self, fun, jac, bounds, npoints, method):
        """
        Find possible roots of a scalar function
        Parameters
        ----------
        fun : function
                    scalar function
        jac : function
            first order derivative of the function
        bounds : tuple
            (min,max) interval for the roots search
        npoints : int
            maximum number of roots to output
        method : str
            'regular' : regular sample of the search interval, 'random' : uniform (distribution) sample of the search interval
        Returns
        ----------
        numpy.array
            possible roots of the function
        """
        if method == 'regular':
            step = (bounds[1] - bounds[0]) / (npoints + 1)
            try:
                x_sampled = np.arange(bounds[0] + step, bounds[1], step)
            except ArithmeticError:
                x_sampled = np.random.uniform(bounds[0], bounds[1], npoints)
        elif method == 'random':
            x_sampled = np.random.uniform(bounds[0], bounds[1], npoints)

        def obj_fun(x_sampled, f, jac):
            g = 0
            j = np.zeros(x_sampled.shape)
            i = 0
            for x in x_sampled:
                fx = f(x)
                g = g + fx**2
                j[i] = 2 * fx * jac(x)
                i = i + 1
            return g, j

        opt = minimize(
            lambda X: obj_fun(X, fun, jac),
            x_sampled,
            method='L-BFGS-B',
            jac=True,
            bounds=[bounds] * len(x_sampled),
        )

        x_opt = opt.x
        np.round(x_opt, decimals=5)
        return np.unique(x_opt)

    def _log_likelihood(self, y, gamma, sigma):
        """
        Compute the log-likelihood for the Generalized Pareto Distribution (μ=0)
        Parameters
        ----------
        y : numpy.array
                    observations
        gamma : float
            GPD index parameter
        sigma : float
            GPD scale parameter (>0)
        Returns
        ----------
        float
            log-likelihood of the sample y to be drawn from a GPD(γ,σ,μ=0)
        """
        n = y.size
        if gamma != 0:
            tau = gamma / sigma
            log_likelihood = (
                -n * log(sigma)
                - (1 + (1 / gamma)) * (np.log(1 + tau * y)).sum()
            )
        else:
            log_likelihood = n * (1 + log(abs(y.mean()) + 1e-8))

        return log_likelihood

    def _quantile(self, side, gamma, sigma):

        if side == 'up':
            r = self.window_len * self.prob / self.num_threshold[side]

            if gamma != 0:
                return self.init_threshold[side] + (sigma / gamma) * (
                    pow(r, -gamma) - 1
                )
            else:
                return self.init_threshold[side] - sigma * log(r)
        elif side == 'down':
            r = self.window_len * self.prob / self.num_threshold[side]

            if gamma != 0:
                return self.init_threshold[side] - (sigma / gamma) * (
                    pow(r, -gamma) - 1
                )
            else:
                return self.init_threshold[side] + sigma * log(r)
        else:
            raise ValueError('The side is not right')

    def _init_drift(self, verbose=False):

        for side in ['up', 'down']:
            self._update_one_side(side)

        return self

    def _update_one_side(self, side: str):

        if side == 'up':
            self.history_peaks[side] = heapq.nlargest(
                self.num_threshold[side],
                list(self.window) + self.history_peaks[side],
            )
            self.init_threshold[side] = self.history_peaks[side][-1]
            self.peaks[side] = np.array(self.history_peaks[side]) - np.array(
                self.init_threshold[side]
            )
        elif side == 'down':
            self.history_peaks[side] = heapq.nsmallest(
                self.num_threshold['down'],
                list(self.window) + self.history_peaks[side],
            )
            self.init_threshold[side] = self.history_peaks[side][-1]
            self.peaks[side] = np.array(self.init_threshold[side]) - np.array(
                self.history_peaks[side]
            )

        # remove the largest incase the first anomaly change the threshold
        # self.peaks[side] = self.peaks[side][1:]
        gamma, sigma, _ = self._grimshaw(side)
        self.extreme_quantile[side] = self._quantile(side, gamma, sigma)
        self.gamma[side] = gamma
        self.sigma[side] = sigma

    def _cal_back_mean(self, data):
        back_mean = (
            np.mean(self.back_mean_window)
            if self.back_mean_window.maxlen > 0
            else np.array(0.0)
        )

        return data - back_mean

    def fit(self, data: Union[float, int]):


        self.back_mean_window.append(data)

        if self.index >= self.back_mean_len:
            self.normal_X = self._cal_back_mean(data)
            self.window.append(self.normal_X)

        if self.index == self.window_len:
            self._init_drift()

        if self.index >= self.window_len:

            last_data = (
                self.window[-2]
                if self.back_mean_len == 0
                else (data - self.window[-1])
            )

            if (
                abs(
                    np.divide(
                        data - last_data, last_data, np.array(data), where=last_data != 0
                    )
                )
                < self.deviance_ratio
            ):
                return self

            if self.normal_X > self.init_threshold['up']:
                self._update_one_side('up')

            elif self.normal_X < self.init_threshold['down']:

                self._update_one_side('down')

        return self

    def score(self, data: Union[float, int]) -> float:


        last_data = (
            self.window[-2]
            if self.back_mean_len == 0
            else (data - self.window[-1])
        )

        if (
            abs(np.divide(data - last_data, last_data, np.array(data), where=last_data != 0))
            < self.deviance_ratio
        ):
            score = 0.0

        elif (
            self.normal_X > self.extreme_quantile['up']
            or self.normal_X < self.extreme_quantile['down']
        ):
            score = 1.0

        elif self.normal_X > self.init_threshold['up']:
            side = 'up'
            score = np.divide(
                self.normal_X - self.init_threshold[side],
                (self.extreme_quantile[side] - self.init_threshold[side]),
                np.array(0.5),
                where=(
                    self.extreme_quantile[side] - self.init_threshold[side] != 0
                ),
            )

        elif self.normal_X < self.init_threshold['down']:
            side = 'down'
            score = np.divide(
                self.init_threshold[side] - self.normal_X,
                (self.init_threshold[side] - self.extreme_quantile[side]),
                np.array(0.5),
                where=(
                    self.init_threshold[side] - self.extreme_quantile[side] != 0
                ),
            )
        else:
            score = 0.0

        # self.thup.append(self.extreme_quantile['up'] + hist_mean)
        # self.thdown.append(self.extreme_quantile['down'] + hist_mean)

        return float(score)
