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

from logging import getLogger

from drain3.masking import LogMasker
from drain3.template_miner import config_filename
from drain3.template_miner_config import TemplateMinerConfig

logger = getLogger(__name__)
config = None
if config is None:
    logger.info(f'Loading configuration from {config_filename}')
    config = TemplateMinerConfig()
    config.load(config_filename)
log_masker = LogMasker(config.masking_instructions, config.mask_prefix, config.mask_suffix)

print(log_masker.mask_prefix)


def get_mask(log_body: str):
    try:
        mask_content = log_masker.mask(log_body)
        # print(mask_content)
        return mask_content
    except Exception as e:
        print('Unable to process log:', e)


in_log_file = 'log/compressor/hadoop-hdfs-datanode-mesos-28.log'


def get_lines():
    with open(in_log_file) as f:

        count = 0
        for each_line in f:
            get_mask(each_line)
            count += 1
            if count > 50000:
                return


if __name__ == '__main__':
    import time

    start = time.time()
    get_lines()
    end = time.time()
    print(f'cost time: {end - start}')
    print('Done')
    # 500k cost 19 seconds
