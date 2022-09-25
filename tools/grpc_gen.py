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
This script is used by Makefile to generate code from protobuf files.
TODO: replace with pure poetry script
"""
import glob
import os
import re
from pathlib import Path

from grpc_tools import protoc

DEST_FOLDER_NAME = 'generated'


def protos(src_dir: str) -> str:
    print(f'============================== Starting at src_dir: {src_dir}')
    if not os.path.exists(src_dir):
        print(
            f'src_dir `{src_dir}` does not exist in the current directory, '
            f'please run this script from the root directory of the project || simply `make gen`')

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.proto'):
                file_path = os.path.normpath(os.path.join(root))
                yield file, file_path


def codegen(proto_location: str):
    out_path = os.path.normpath(os.path.join(proto_location, DEST_FOLDER_NAME))
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    Path((os.path.join(out_path, '__init__.py'))).touch()
    protoc.main(['grpc_tools.protoc',
                 f'--proto_path={proto_location}',
                 f'--python_out={out_path}',
                 f'--grpc_python_out={out_path}'
                 ] + list(glob.iglob(f'{proto_location}/*.proto')))

    search_path = os.path.join(out_path, '*.py')
    for py_file in glob.iglob(os.path.join(search_path)):
        Path(os.path.join(os.path.dirname(py_file), '__init__.py')).touch()
        with open(py_file, 'r+') as file:
            code = file.read()
            file.seek(0)
            replaced_inplace = re.sub(r'(import .+_pb2.*)', 'from . \\1', code)
            replaced_nested = re.sub(r'from (.+) (import .+_pb2.*)', 'from ..\\1 \\2', replaced_inplace)
            file.write(replaced_nested)
            file.truncate()


if __name__ == '__main__':
    for proto_name, proto_path in protos(src_dir='engine'):
        print(f'Resolving `{proto_name}` at `{proto_path}`')
        codegen(proto_location=proto_path)
    else:
        print('============================== Finished ==============================')
