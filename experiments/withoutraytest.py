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
This module is an POC for the Ray-based (distributed) version of log processor.
"""
import time
import zlib
from logging import getLogger

import redis.exceptions
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
        # 处理数据，讲获取到的log_message 和service 进行masking
        mask_content = log_masker.mask(log_body)
        # print(mask_content)
        return mask_content
    except Exception as e:
        print('Unable to process log:', e)


class RayConsumer(object):
    """
    This Ray Consumer will consume each log entry from the
    Redis stream and process each with Drain masker, then pass the
    data into the template miner (DrainActor) for learning.
    --------------------------------------------------------
    This is a ray actor * many instances made to be immortal and runs forever.
    1. TODO: fault tolerance is handled by checkpoints
    https://docs.ray.io/en/master/ray-core/actors/patterns/fault-tolerance-actor-checkpointing.html
    2. the actor will be restarted if it crashes
    """

    # 创建一个stram的consumer group 并连接到redis数据库中
    def __init__(self, i):
        # if os.path.exists("/tmp/checkpoint.pkl"):
        #     self.state = pickle.load(open("/tmp/checkpoint.pkl"))
        # else:
        #     self.state = MyState()

        self.run = None
        import redis

        hostname = 'localhost'
        port = 49153
        r = redis.Redis(hostname, port, retry_on_timeout=True, username='default', password='redispw')

        self.group_name = 'test_consumer_group'
        self.consumer_id = i
        self.r = r
        try:
            # start from 0 (the beginning of the stream), always,
            # we use xdel/trim [len(stream)-count(acked)] to
            # delete the acked messages
            self.r.xgroup_create('test', self.group_name, id='0', mkstream=False)
        except redis.exceptions.ResponseError as e:
            pass
        try:
            self.r.xgroup_createconsumer('test', self.group_name, f'consumer-{self.consumer_id}')
        except:
            pass

    def start(self):
        self.run = True
        processed_counter = 0  # this records the logs processed, TODO fail safe for workers crash and redis crash
        time_readgroup_total = 0
        time_ack_total = 0
        time_delete_total = 0
        while self.run:
            try:
                time_readgroup_start = time.time()
                msg = self.r.xreadgroup(
                    groupname=self.group_name,
                    consumername=f'consumer-{self.consumer_id}',
                    streams={'test': '>'},
                    count=1000,  # if blocked, count will not take effect as always be 1
                    block=100,  # block for 1 year before it can timeout
                )
                time_readgroup_end = time.time()
                time_readgroup_total += time_readgroup_end - time_readgroup_start
            except redis.exceptions.TimeoutError as e:
                return
            if not msg:
                # for testing only, we should wait indefinitely if there is no message in production
                print(f'time_readgroup_total: {time_readgroup_total} seconds')
                print(f'time_ack_total {time_ack_total} seconds')
                print(f'time_delete_total {time_delete_total} seconds')
                return

            # also update the id of current log, to prevent crash of consumer group
            # print(msg)
            try:
                # for single
                # [[stream, [[entry_id, log_entry]]]] = msg if msg != [] else [[None], [[None, None]]]

                # for micro batch
                stream, entries = msg[0]
                processed_counter += len(entries)  # not always count, when blocked it will be +1

                # print(f'got {len(entries)} entries from stream {stream}')
                # print(f'data from stream {stream} entry_id {entry_id} \n log_entry {log_entry}')
            except Exception as e:
                print(e)
                print(msg)
                continue
            for log_entry_id, log_entry in entries:
                try:
                    log_body = zlib.decompress(log_entry[b'log_compressed']).decode('utf-8')
                    # log_body = log_entry[b'log_compressed'].decode('utf-8')
                except:
                    print(log_entry)
                    continue
                try:
                    # masked = ray.get(get_mask.remote(log_body)) # todo this is slower than directly masking
                    mask_content = log_masker.mask(log_body)
                    # print(mask_content)

                    # after success masking, we should ack the message then delete it from the stream
                except Exception as e:
                    print(log_body)
                    print(e)
            log_ids_to_respond = [lid for lid, entry in entries]
            try:
                time_ack_start = time.time()
                self.r.xack('test', self.group_name, *log_ids_to_respond)
                time_ack_end = time.time() - time_ack_start
                time_ack_total += time_ack_end
                time_delete_start = time.time()
                self.r.xdel('test', *log_ids_to_respond)  # xtrim is dangerous, need evaluation
                time_delete_end = time.time() - time_delete_start
                time_delete_total += time_delete_end
            except Exception as e:
                print(e)

    def stop(self):
        self.run = False

    def destory(self):
        self.r.connection_pool.disconnect()


if __name__ == '__main__':
    from experiments.log.compressor.redis_gen import main

    main(count=500000, batch_size=2000)

    start_time = time.time()
    consumer = RayConsumer(0)
    consumer.start()
    print(f'finished in {time.time() - start_time} seconds')

    # size of log in Mega byte 86.237173MB
    # Time taken to send 50k messages with batch 2000: 14.056486368179321 seconds
    # time_readgroup_total: 8.538283109664917 seconds
    # time_ack_total 3.314781427383423 seconds
    # time_delete_total 10.87747597694397 seconds
    # finished in 46.85015392303467 seconds
