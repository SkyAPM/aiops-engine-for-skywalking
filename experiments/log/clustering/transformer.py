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
from os import environ
from os.path import dirname

import ray

import redis
from cachetools import LRUCache
from redis import Redis

from drain3.drain import Drain
from drain3.masking import LogMasker
from drain3.template_miner import LogCache
from drain3.template_miner_config import TemplateMinerConfig

ray.init()

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

persistence_type = 'REDIS'
config = TemplateMinerConfig()
config.load(dirname(__file__) + '/drain3.ini')

log_masker = LogMasker(config.masking_instructions, config.mask_prefix, config.mask_suffix)


@ray.remote
def get_data(data):
    if not data or not data[0] or not data[0][1]:
        return None, None
    for item in data[0][1]:
        if not item:
            return None, None

        msg_id = str(item[0], 'utf-8')
        data = {}
        for key in item[1].keys():
            k = str(key, 'utf-8')
            try:
                v = str(item[1][key], 'utf-8')
            except Exception:
                val = zlib.decompress(item[1][key])
                v = str(val, 'utf-8')
            data[k] = v
    return msg_id, data


@ray.remote(num_cpus=1)
def get_mask(log_body):
    try:

        # preprocess log message
        mask_content = log_masker.mask(log_body)

        return mask_content



    except Exception as e:
        print('Unable to process log:', e)


@ray.remote(num_cpus=0.05)
class RayConsumer(object):
    def __init__(self):
        # connect to redis and create consumer group
        hostname = environ.get('REDIS_HOSTNAME', 'redis-com')
        port = environ.get('REDIS_PORT', 123)
        self.r = Redis(hostname, port, retry_on_timeout=True, username='default',
                       password='password')
        try:
            self.r.xgroup_create('test', 'ray_group3', id='0')
        except redis.exceptions.ResponseError:
            pass

    def start(self):
        self.run = True

        while self.run:
            # get log message from redis
            log = self.r.xreadgroup('consumer_group_name', 'consumer', {'stream_name': '>'}, count=1)

            if log is None:
                continue
            log_id, log_body = ray.get(get_data.remote(log))
            self.r.xack('stream_name', 'consumer_group_name', log_id)
            self.r.xdel('stream_name', log_id)
            # preprocess to log
            log_message = log_body['log_compressed']
            log_service = log_body['service']
            print(log_message)
            mask = ray.get(get_mask.remote(log_message))


            # clustering
            drain = ray.get_actor('drain')
            result = ray.get(drain.get_cluster.remote(mask, log_service))

            # put template message to redis
            producer = ray.get_actor('producer')
            # Final result are put into redis
            ray.get(producer.put_template.remote(result, id, log_service))

    def stop(self):
        self.run = False

    def destroy(self):
        self.r.close()


@ray.remote
class DrainCluster:
    def __init__(self):
        param_str = config.mask_prefix + '*' + config.mask_suffix
        self.drain = Drain(
            sim_th=config.drain_sim_th,
            depth=config.drain_depth,
            max_children=config.drain_max_children,
            max_clusters=config.drain_max_clusters,
            max_logs=config.drain_max_logs,
            extra_delimiters=config.drain_extra_delimiters,
            param_str=param_str,
            parametrize_numeric_tokens=config.parametrize_numeric_tokens
        )
        self.num_mask = 0
        self.log_cache = LogCache(self.drain.max_logs)
        self.log_cluster_cache = LogCache(self.drain.max_logs)
        self.parameter_extraction_cache = LRUCache(config.parameter_extraction_cache_capacity)

    def get_cluster(self, mask_content, log_service):
        mask_id = self.log_cache.get(mask_content)
        if mask_id is None:

            self.log_cache[mask_content] = self.num_mask

            # get cluster and cluster_type
            cluster, change_type = self.drain.add_log_message(mask_content, log_service)
            self.log_cluster_cache[self.num_mask] = cluster


        else:
            cluster = self.log_cluster_cache.get(mask_id)
            cluster.size += 1
            self.drain.id_to_cluster[cluster.cluster_id]
            change_type = 'none'

        result = {
            'change_type': change_type,
            'cluster_id': cluster.cluster_id,
            'cluster_size': cluster.size,
            'template_mined': cluster.get_template(),
            'cluster_count': len(self.drain.clusters)
        }

        return result


@ray.remote
class RayProducer:
    def __init__(self):
        hostname = environ.get('REDIS_HOSTNAME', 'redis-com')
        port = environ.get('REDIS_PORT', 123)
        self.r = Redis(hostname, port, retry_on_timeout=True, username='default',
                       password='password')

    def put_template(self, result, log_id, log_service):
        template_id = result['cluster_id']
        change_mind = result['change_type']
        template = result['template_mined']
        service_template_id = log_service + str(template_id)

        id_log_template = {'service_template_id': service_template_id, 'log_id': log_id}

        self.r.xadd('log_template', id_log_template)

        if change_mind == 'cluster_template_changed' or change_mind == 'cluster_created':
            self.r.hset('change_template', service_template_id, template)

    def destroy(self):
        self.r.close()


consumers = [RayConsumer.remote() for _ in range(5)]
drain = DrainCluster.options(name='drain').remote()
producer = RayProducer.options(name='producer').remote()

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
