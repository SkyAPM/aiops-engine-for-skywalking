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
import shutil


def find_and_clean(folders_to_remove: list, root='.') -> None:
    """
    Find and clean all files in the given folder list
    :param folders_to_remove: list of directories to remove
    :param root: from which folder to start searching, default current
    :return:
    """
    exclude: set = {'.venv'}
    for path, dirs, _ in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude]
        for folder in folders_to_remove:
            if any(folder in d for d in dirs):
                shutil.rmtree(removed := os.path.join(path, folder))
                print(f'Removed {removed}')


if __name__ == '__main__':
    find_and_clean(folders_to_remove=['__pycache__', 'generated', 'build', 'dist',
                                      'egg-info', 'pytest_cache', '.pyc'],
                   root='.')
