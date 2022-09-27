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
This log ingestor is used to ingest raw log data from a gRPC client,
connects to your own client as long as it follows the data protocol.

Refer to https://grpc.io/docs/languages/ for implementing
your own exporter from any data source.
"""
import asyncio
import logging
import multiprocessing

import grpc
import yappi

from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2_grpc
from engine.providers.skywalking.log.grpc.servicers.aio_servicer import LogIngestorServicer

_PROCESS_COUNT = multiprocessing.cpu_count()
_THREAD_CONCURRENCY = _PROCESS_COUNT

print(f'Count of processes {_PROCESS_COUNT}')

yappi.set_clock_type('WALL')


async def serve() -> None:
    server = grpc.aio.server()
    log_exporter_pb2_grpc.add_LogExportServiceServicer_to_server(LogIngestorServicer(), server)
    # print(log_exporter_pb2.DESCRIPTOR.services_by_name.keys())
    # service_names = (
    #     log_exporter_pb2.DESCRIPTOR.services_by_name['LogExportService'].full_name,
    #     reflection.SERVICE_NAME,
    # )
    # reflection.enable_server_reflection(service_names, server)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    logging.info('Starting server on %s', listen_addr)
    await server.start()
    await server.wait_for_termination()



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # send_data(connect_to_redis(), 10000)
    loop = asyncio.get_event_loop()
    loop.create_task(serve())
    loop.run_forever()
