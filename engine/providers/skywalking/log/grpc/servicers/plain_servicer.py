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
import time
import zlib

from engine.utils.logging_mixin import LoggingMixin

try:
    from typing import Iterable
except ImportError:
    from collections.abc import Iterable

import grpc
import yappi
from redis import asyncio as aioredis  # noqa
from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2, log_exporter_pb2_grpc

yappi.set_clock_type('WALL')


class LogIngestorServicer(log_exporter_pb2_grpc.LogExportServiceServicer, LoggingMixin):
    def __init__(self, redis_info: dict):
        ...
        self.redis_info = redis_info
        self.last_report_time = None

        # self.channel = grpc.insecure_channel('localhost:50051')  # no need await here
        # self.stub = log_exporter_pb2_grpc.LogExportServiceStub(channel=self.channel)
        async def get_redis():
            redis_conn = await aioredis.from_url(redis_info['REDIS_HOSTNAME'] + ':' + redis_info['REDIS_PORT'],
                                                 retry_on_timeout=True, username=redis_info['username'],
                                                 password=redis_info['password'])
            return redis_conn

        self.redis_conn = await get_redis()

    def AskSubscription(self, request: log_exporter_pb2.SubscriptionRequest,
                        context: grpc.aio.ServicerContext) -> log_exporter_pb2.SubscriptionRequest:
        # request = client ask what do you want?
        self.logger.info('subscription request: %s', request)
        res = log_exporter_pb2.SubscriptionResponse(serviceID=['1', '2', '3'])

        return res
        # 客户端流模式（在一次调用中, 客户端可以多次向服务器传输数据, 但是服务器只能返回一次响应）
        # stream-unary (In a single call, the client can transfer data to the server several times,
        # but the server can only return a response once.)

    def StreamLogExport(self, request_iterator, context):
        print('ClientStreamingMethod called by client...')
        count = 0

        with yappi.run():
            pipeline = self.redis_conn.pipeline()
            batch_size = 0
            last_submit = time.time()
            for request in request_iterator:
                batch_size += 1
                # replace zlib with zstd compressor (dict)
                data = {
                    'producer': 'oap',
                    'log_compressed': zlib.compress(request.body.content.encode()),  # Just some random data
                    'service': 'servicetest',
                }
                pipeline.xadd('test', data)
                if self.last_report_time - time.time() > 5:
                    pipeline.execute()
                if batch_size == 1000:
                    # send the pipeline
                    batch_size = 0
                    resp = pipeline.execute()
                    last_submit = time.time()
                    print(resp)
                if batch_size != 0 and time.time() - last_submit > 5:
                    resp = pipeline.execute()
                    print(resp)
                    print('send pipeline for after 5 seconds passed')
                # print(f"request: {str(request.rawLog)}")
                if count % 1000 == 0:
                    print(f'working on line #{count}')
                if count == 100000:
                    print(count)
                    print(f'received {count} logs')
                    yappi.get_func_stats().print_all()
                    exit()
                count += 1
            return log_exporter_pb2.ExportResponse(receivedCount=count)
