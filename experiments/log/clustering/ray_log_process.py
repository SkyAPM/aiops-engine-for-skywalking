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

import logging
import sys
import time
import zlib
from os.path import dirname

import ray
import redis
from redis import Redis

from drain_parser.masking import LogMasker
from drain_parser.template_miner import TemplateMiner
from drain_parser.template_miner_config import TemplateMinerConfig

ray.init()

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

persistence_type = 'REDIS'
config = TemplateMinerConfig()
config.load(dirname(__file__) + '/drain3.ini')

log_masker = LogMasker(config.masking_instructions, config.mask_prefix, config.mask_suffix)
template_miner = TemplateMiner(config=config)


@ray.remote(num_cpus=0.05)
class RayConsumer(object):
    def __init__(self, i, redis_conn, stream_name: str):
        """
        The whole process of log outlier detection
        Read log message from Redis in the form of stream
        mask log message, and cluster by using mask and service
        put cluster message to redis
        """
        # connect to redis and create consumer group
        self.run = None
        self.r = Redis(redis_conn['REDIS_HOSTNAME'], redis_conn['REDIS_PORT'],
                       retry_on_timeout=True, username=redis_conn['username'],
                       password=redis_conn['password'])
        try:
            self.r.xgroup_create('test', 'ray_group3', id='0')
        except redis.exceptions.ResponseError as e:
            print(e)
            pass
        self.consumer_id = i
        self.group_name = 'ray_group3'
        self.stream_name = stream_name

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
                    block=86_400_000,  # block for 1 day before it can timeout and shutdown
                )
                time_readgroup_end = time.time()
                time_readgroup_total += time_readgroup_end - time_readgroup_start
            except redis.exceptions.TimeoutError as e:
                print('timeout')
                return
            if not msg:
                # for testing only, we should wait indefinitely if there is no message in production
                print(f'time_readgroup_total: {time_readgroup_total} seconds')
                print(f'time_ack_total {time_ack_total} seconds')
                print(f'time_delete_total {time_delete_total} seconds')
                # return

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
            pipeline = self.r.pipeline()
            for log_entry_id, log_entry in entries:
                try:
                    log_body = zlib.decompress(log_entry[b'log_compressed']).decode('utf-8')
                    # log_body = log_entry[b'log_compressed'].decode('utf-8')
                except zlib.error as e:
                    print(log_entry)
                    continue
                try:
                    # masked = ray.get(get_mask.remote(log_body)) # todo this is slower than directly masking
                    mask_content = log_masker.mask(log_body)
                    # print(mask_content)
                    service = 'testoap'
                    # ref = drain_remote.learn_one.remote(masked_content=mask_content, service=service)
                    result = template_miner.get_cluster(mask_content, service)
                    # put template message to redis
                    template_id = result['cluster_id']
                    change_type = result['change_type']
                    template = result['template_mined']
                    service_template_id = service + str(template_id)
                    id_log_template = {'service_template_id': service_template_id, 'log_id': log_entry_id}
                    pipeline.xadd('log_template', id_log_template)
                    # self.r.xadd('log_template', id_log_template)

                    if change_type == 'cluster_template_changed' or change_type == 'cluster_created':
                        pipeline.hset('change_template', service_template_id, template)

                    # producer = ray.get_actor('producer')
                    # Final result are put into redis
                    # ray.get(producer.put_template.remote(result, log_entry_id, service))
                    # after success masking, we should ack the  then delete it from the stream
                except Exception as e:
                    print(log_body)
                    print(e)
            pipeline.execute()
            log_ids_to_respond = [lid for lid, entry in entries]
            print(log_ids_to_respond)
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
                print('failed to ack', e)

    def stop(self):
        self.run = False

    def destroy(self):
        self.r.close()


@ray.remote
class RayProducer:
    def __init__(self, redis_conn):
        """
        put cluster and template message to Redis
        """
        self.r = Redis(redis_conn['REDIS_HOSTNAME'], redis_conn['REDIS_PORT'],
                       retry_on_timeout=True, username=redis_conn['username'],
                       password=redis_conn['password'])

    def put_template(self, result, log_id, log_service):
        template_id = result['cluster_id']
        change_type = result['change_type']
        template = result['template_mined']
        service_template_id = log_service + str(template_id)
        id_log_template = {'service_template_id': service_template_id, 'log_id': log_id}
        self.r.xadd('log_template', id_log_template)

        if change_type == 'cluster_template_changed' or change_type == 'cluster_created':
            self.r.hset('change_template', service_template_id, template)

    def destroy(self):
        self.r.close()


if __name__ == '__main__':

    from secrets_temp import redis_info

    consumers = [RayConsumer.remote(i, redis_info, stream_name='test') for i in range(1)]
    producer = RayProducer.options(name='producer').remote(redis_info)

    try:
        refs = [c.start.remote() for c in consumers]
        ray.get(refs)
    except KeyboardInterrupt:
        for c in consumers:
            c.stop.remote()
    finally:
        for c in consumers:
            c.destroy.remote()

        producer.destroy.remote()
