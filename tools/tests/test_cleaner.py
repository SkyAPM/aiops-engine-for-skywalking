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
import os

from tools import cleaner


# import pytest


def generate_garbage():
    print(os.getcwd())
    os.makedirs("abc.pyc", exist_ok=True)


def test_find_and_clean():
    cleaner.find_and_clean(folders_to_remove=['abc.pyc'], root='.')


if __name__ == '__main__':
    generate_garbage()
    test_find_and_clean()
