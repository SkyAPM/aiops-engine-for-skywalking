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

import zlib
from sys import getsizeof

from pyzstd import RichMemZstdCompressor, ZstdCompressor, train_dict

from engine.utils.timer import timing

zstd_compressor = ZstdCompressor()
zstd_rich_compressor = RichMemZstdCompressor()

repeat_test = 1
test_file = 'hadoop-28-min.log' or 'hadoop-hdfs-datanode-mesos-28.log'


def log_gen():
    with open(file=test_file, mode='r') as log_file:
        temp_log = ''
        count = 0
        for log in log_file:
            if log.startswith('20'):
                if temp_log:
                    yield temp_log
                    temp_log = ''
                yield log
                count += 1
            else:
                temp_log += log
                continue


@timing(repeat=repeat_test)
def compress_zstd() -> None:
    compressed_size = 0
    for log in log_gen():
        zstd_compressor.compress(log.encode())
        compressed_log = zstd_compressor.flush()
        compressed_size += getsizeof(compressed_log)

    print(f'zstd compressed size: {compressed_size / 1024 / 1024:.2f} MB')


@timing(repeat=repeat_test)
def compress_rich_zstd() -> None:
    compressed_size = 0
    for log in log_gen():
        compressed_log = zstd_rich_compressor.compress(log.encode())
        compressed_size += getsizeof(compressed_log)

    print(f'zstd-rich compressed size: {compressed_size / 1024 / 1024:.2f} MB')


@timing(repeat=repeat_test)
def compress_with_dict_zstd() -> None:
    with open(file='training_dict_samples.txt', mode='br') as train_in:
        zstd_dict = train_dict(samples=train_in, dict_size=10000)
        zstd_dict_compressor = ZstdCompressor(zstd_dict=zstd_dict)

    compressed_size = 0
    for log in log_gen():
        zstd_dict_compressor.compress(log.encode())
        compressed_log = zstd_dict_compressor.flush()
        compressed_size += getsizeof(compressed_log)

    print(f'zstd-dict compressed size: {compressed_size / 1024 / 1024:.2f} MB')


@timing(repeat=repeat_test)
def compress_zlib() -> None:
    compressed_size = 0
    for log in log_gen():
        compressed_log = zlib.compress(log.encode())
        compressed_size += getsizeof(compressed_log)

    print(f'zlib compressed size: {compressed_size / 1024 / 1024:.2f} MB')


if __name__ == '__main__':

    original_size = 0
    for log_data in log_gen():
        original_size += getsizeof(log_data.encode())
    print(f'log size before compression: {original_size / 1024 / 1024:.2f} MB')
    compress_zstd()
    compress_rich_zstd()
    compress_with_dict_zstd()
    compress_zlib()
