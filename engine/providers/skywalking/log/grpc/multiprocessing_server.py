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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import datetime
import logging
import multiprocessing
import socket
import sys
import time
from concurrent import futures

import grpc

from engine.providers.skywalking.log.grpc.proto.generated import log_exporter_pb2_grpc
from servicer import LogIngestorServicer

_LOGGER = logging.getLogger(__name__)
_ONE_DAY = datetime.timedelta(days=1)
_PROCESS_COUNT = multiprocessing.cpu_count() - 14
print(f'Count of processes {_PROCESS_COUNT}')
_THREAD_CONCURRENCY = _PROCESS_COUNT


def _wait_forever(server):
    try:
        while True:
            time.sleep(_ONE_DAY.total_seconds())
    except KeyboardInterrupt:
        server.stop(None)


def _run_server(bind_address):
    """Start a server in a subprocess."""
    _LOGGER.info('Starting new server.')
    options = (('grpc.so_reuseport', 1),)
    server = grpc.server(futures.ThreadPoolExecutor(
        max_workers=_THREAD_CONCURRENCY, ),
        options=options)
    log_exporter_pb2_grpc.add_LogExportServiceServicer_to_server(LogIngestorServicer(), server)
    server.add_insecure_port(bind_address)
    server.start()
    server.wait_for_termination()  # _wait_forever(server)


@contextlib.contextmanager
def _reserve_port(bind_strategy):
    """Find and reserve a port for all subprocesses to use."""
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    # for windows!
    # https://stackoverflow.com/questions/14388706/how-do-so-reuseaddr-and-so-reuseport-differ
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 0)
    sock.setsockopt(socket.SOL_SOCKET, bind_strategy, 1)
    if sock.getsockopt(socket.SOL_SOCKET, bind_strategy) == 0:
        raise RuntimeError("Failed to set SO_REUSEPORT.")
    sock.bind(('', 0))
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


def main(bind_strategy):
    with _reserve_port(bind_strategy=bind_strategy) as port:
        bind_address = 'localhost:{}'.format(port)
        _LOGGER.info("Binding to '%s'", bind_address)
        sys.stdout.flush()
        workers = []
        for _ in range(_PROCESS_COUNT):
            # NOTE: It is imperative that the worker subprocesses be forked before
            # any gRPC servers start up. See
            # https://github.com/grpc/grpc/issues/16001 for more details.

            worker = multiprocessing.Process(target=_run_server,
                                             args=(bind_address,))
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join()


if __name__ == '__main__':
    from sys import platform

    if platform == "linux" or platform == "linux2":
        strategy = socket.SO_REUSEPORT
    elif platform == "darwin":
        strategy = socket.SO_REUSEPORT
    elif platform == "win32":
        strategy = socket.SO_REUSEADDR
    else:
        strategy = socket.SO_REUSEADDR
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[PID %(process)d] %(message)s')
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    main(bind_strategy=strategy)
