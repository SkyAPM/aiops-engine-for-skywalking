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
    def __init__(self, redis_conn):
        """
        The whole process of log outlier detection
        Read log message from Redis in the form of stream
        mask log message, and cluster by using mask and service
        put cluster message to redis
        """
        # connect to redis and create consumer group
        self.r = Redis(redis_conn['REDIS_HOSTNAME'], redis_conn['REDIS_PORT'],
                       retry_on_timeout=True, username=redis_conn['username'],
                       password=redis_conn['password'])
        try:
            self.r.xgroup_create('test', 'ray_group3', id='0')
        except redis.exceptions.ResponseError:
            pass

    def start(self):
        self.run = True

        while self.run:
            # get log message from redis
            message = self.r.xreadgroup('consumer_group_name', 'consumer', {'stream_name': '>'}, count=1)
            stream, entry = message[0]
            log_id, log = entry[0]
            log_body = {}
            for key in log.keys():
                k = str(key, 'utf-8')
                if k == 'log_compressed':
                    try:
                        v = zlib.decompress(log[key]).decode('utf-8')
                    except zlib.error:
                        pass
                else:
                    v = str(log[key], 'utf-8')
                log_body[k] = v
            self.r.xack('stream_name', 'consumer_group_name', log_id)
            self.r.xdel('stream_name', log_id)
            # preprocess to log
            log_message = log_body['log_compressed']
            log_service = log_body['service']
            mask = log_masker.mask(log_message)
            # clustering
            result = template_miner.get_cluster(mask, log_service)
            # put template message to redis
            producer = ray.get_actor('producer')
            # Final result are put into redis
            ray.get(producer.put_template.remote(result, log_id, log_service))

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

    redis_connection = {'REDIS_HOSTNAME': 'redis.com',
                        'REDIS_PORT': 1234,
                        'username': 'default',
                        'password': 'word'
                        }
    consumers = [RayConsumer.remote(redis_connection) for _ in range(5)]
    producer = RayProducer.options(name='producer').remote(redis_connection)

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
