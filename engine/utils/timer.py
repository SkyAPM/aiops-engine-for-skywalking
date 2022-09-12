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


"""
Timer util for measuring elapsed time.
from tools.timer import timing
decorate @timing on any function to measure
"""
import contextlib
import functools
import math
import timeit

import wrapt


def timing(wrapped: callable = None, show_args: bool = False, repeat: int = 100) -> callable:
    """
    Decorator that reports the execution time of any function.
    NOTE:
    Do not use on recursive functions,
    Careful with functions that can alter external state, such
    as passed generator, files, and network connections.
    :param wrapped: param wrapped: function to be decorated
    :param show_args: If True, show the arguments of the function.
    :param repeat: repeat N times
    :return: decorator
    """
    if wrapped is None:
        return functools.partial(timing, show_args=show_args, repeat=repeat)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):  # noqa
        print(f'--- Timing started for {wrapped.__name__}, will repeat {repeat} times ---')
        with contextlib.redirect_stdout(None):
            execution_time_list = timeit.Timer(functools.partial(wrapped, *args, **kwargs)).repeat(repeat=repeat,
                                                                                                   number=1)
        if show_args:
            print(f'Function:{wrapped.__name__} args:[{args}], kwargs: [{kwargs}]\n'
                  f'min runtime: {min(execution_time_list):f} secs,\n '
                  f'avg runtime: {sum(execution_time_list) / repeat:f} secs')
        else:
            print(f'Function:{wrapped.__name__}\n'
                  f'min runtime: {min(execution_time_list):f} secs,\n'
                  f'avg runtime: {sum(execution_time_list) / repeat:f} secs')
        print(f'--- Timing ended for {wrapped.__name__} ---')
        return wrapped(*args, **kwargs)

    return wrapper(wrapped)


if __name__ == '__main__':
    @timing(show_args=True, repeat=100)
    def factorial(n: int):
        return math.factorial(n)


    factorial(n=100)
