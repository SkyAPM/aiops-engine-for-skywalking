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
import time
import zlib
from collections.abc import Iterable
from os import environ

import grpc
import yappi
from redis import Redis

# from engine.ingestors.base import BaseGRPCIngestor
from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2, log_exporter_pb2_grpc

yappi.set_clock_type('WALL')


class LogIngestorServicer(log_exporter_pb2_grpc.LogExportServiceServicer):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.channel = grpc.insecure_channel('localhost:50051')  # no need await here
        self.stub = log_exporter_pb2_grpc.LogExportServiceStub(channel=self.channel)

    async def StreamLogExport(self, request_iterator: Iterable[log_exporter_pb2.LogData],
                              context: grpc.aio.ServicerContext):

        self.logger.info('Received subscription request: %s', request_iterator)
        count = 0
        print('wtf1')

        async for record in self.stub.StreamLogExport(request_iterator):
            count += 1
            self.logger.info(f'Received log record Number# {count}: {record}')
        return log_exporter_pb2.ExportResponse(receivedCount='got message logs batch ')

    async def Subscribe(self, request: log_exporter_pb2.SubscriptionRequest,
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
        hostname = environ.get('REDIS_HOSTNAME', 'redis-11238.c74.us-east-1-4.ec2.cloud.redislabs.com')
        port = environ.get('REDIS_PORT', 11238)
        r = Redis(hostname, port, retry_on_timeout=True, username='default', password='skywalking')
        with yappi.run():
            pipeline = r.pipeline()
            batch_size = 0
            last_submit = time.time()
            async for request in request_iterator:
                batch_size += 1
                # replace zlib with zstd compressor (dict)
                data = {
                    'producer': 'oap',
                    'log_compressed': zlib.compress(request.rawLog.encode()),  # Just some random data
                    'service': 'servicetest',
                }
                pipeline.xadd('test', data)
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
                    await exit()
                count += 1
            return log_exporter_pb2.ExportResponse(receivedCount=str(count))
