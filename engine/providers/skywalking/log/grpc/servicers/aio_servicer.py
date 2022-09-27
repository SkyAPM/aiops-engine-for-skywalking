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
import asyncio
import zlib

from engine.utils.logging_mixin import LoggingMixin

try:
    from typing import Iterable
except ImportError:
    from collections.abc import Iterable

import grpc
import yappi
from redis import asyncio as aioredis  # noqa

# from engine.ingestors.base import BaseGRPCIngestor
from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2, log_exporter_pb2_grpc

yappi.set_clock_type('WALL')


class LogIngestorServicer(log_exporter_pb2_grpc.LogExportServiceServicer, LoggingMixin):
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn
        self.last_report_time = None
        self.send_queue = asyncio.Queue()

        asyncio.create_task(self.send_to_redis())
        # await self.send_queue.join()

    async def send_to_redis(self):
        while True:
            # We don't need atomic transactions
            async with self.redis_conn.pipeline(transaction=False) as pipe:
                for _ in range(1000):
                    data = await self.send_queue.get()
                    self.send_queue.task_done()
                    await pipe.xadd('test', data)
                await pipe.execute()

    async def AskSubscription(self, request: log_exporter_pb2.SubscriptionRequest,
                              context: grpc.aio.ServicerContext) -> log_exporter_pb2.SubscriptionRequest:
        # request = client ask what do you want?
        self.logger.info('subscription request: %s', request)
        res = log_exporter_pb2.SubscriptionResponse(serviceID=['1', '2', '3'])

        return res
        # 客户端流模式（在一次调用中, 客户端可以多次向服务器传输数据, 但是服务器只能返回一次响应）
        # stream-unary (In a single call, the client can transfer data to the server several times,
        # but the server can only return a response once.)

    async def StreamLogExport(self, request_iterator, context):
        print('ClientStreamingMethod called by client...')
        count = 0
        with yappi.run():
            batch_size = 0
            async for request in request_iterator:
                batch_size += 1
                # replace zlib with zstd compressor (dict)
                data = {
                    'producer': 'oap',
                    'log_compressed': zlib.compress(request.body.content.encode()),  # Just some random data
                    'service': 'servicetest',
                }
                await self.send_queue.put(data)
                count += 1
        return log_exporter_pb2.ExportResponse(receivedCount=count)
