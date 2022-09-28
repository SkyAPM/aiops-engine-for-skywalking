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

"""The Python AsyncIO implementation of the GRPC hellostreamingworld.MultiGreeter client."""

import asyncio
import logging
import os
import time

import grpc

from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2_grpc, log_exporter_pb2
from engine.providers.skywalking.log.grpc.proto.generated.log_exporter_pb2 import LogData, LogDataBody
from engine.utils.timer import timing

os.environ['PYTHONDEVMODE'] = '1'

import yappi  # profiler


@timing
async def run(name) -> None:
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = log_exporter_pb2_grpc.LogExportServiceStub(channel)

        # Read from an async generator
        # subscription = await stub.Subscribe(log_exporter_pb2.SubRequest())
        # print(subscription)
        res = await stub.AskSubscription(log_exporter_pb2.SubscriptionRequest())
        print(res)

        async def generator():
            counter = 0
            try:
                # with open(file='hadoop-28-min.log') as infile:
                #     for log in infile:
                #         counter += 1
                #
                #         yield LogData(body=LogDataBody(content=log))
                #         if counter == 2000:
                #             break
                for i in range(50000):
                    yield LogData(body=LogDataBody(content="""192.168.198.92 - - [22/Dec/2002:23:08:37 -0400] "GET 
   / HTTP/1.1" 200 6394 www.yahoo.com 
   "-" "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1...)" "-"
192.168.198.92 - - [22/Dec/2002:23:08:38 -0400] "GET """))

            except Exception as e:
                print(e)

        start = time.time()
        response = await stub.StreamLogExport(generator())
        print(f'time.time() - start = {time.time() - start}')
        print(response)

        print('-------------- EXPORT OVER ---------------')


async def main():
    yappi.set_clock_type('WALL')
    task1 = asyncio.create_task(
        run(name='0000001'))

    # task2 = asyncio.create_task(
    #     run(name='0000002'))
    with yappi.run():
        await task1
        # await task2
    # yappi.get_func_stats().print_all()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
