# Copyright 2025 TOYOTA MOTOR CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import grpc  # type: ignore[import-untyped]

from .compiler import compile_proto
from .proto_interface import init_proto
from .grpc_interface import init_grpc, init_server, init_client, del_client, get_client_channel

def init() -> None:
    dynamic_pb2, dynamic_pb2_grpc = compile_proto()
    init_proto(dynamic_pb2)
    init_grpc(dynamic_pb2_grpc)

def serve(port: int, host: str | None = None) -> None:
    init()
    server = init_server(port, host)
    server.start()
    bind_target = f"{host}:{port}" if host is not None else f"port {port}"
    print(f"Server started on {bind_target} (pid = {os.getpid()}).")
    server.wait_for_termination()

def connect(hostname: str, port: int, timeout: float = 5.0) -> None:
    init()
    init_client(hostname, port)
    try:
        grpc.channel_ready_future(get_client_channel()).result(timeout=timeout)
    except grpc.FutureTimeoutError:
        del_client()
        raise ConnectionError(f"Failed to connect to server {hostname}:{port} within {timeout}s")
    print(f"Client connected to server {hostname}:{port} (pid = {os.getpid()}).")

def disconnect() -> None:
    del_client()
