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

from __future__ import annotations
from typing import TypeVar, Callable, Type, Any, Optional, cast, TYPE_CHECKING
from typing_extensions import ParamSpec, dataclass_transform
import functools
import dataclasses

from .compiler import compile_function, compile_dataclass, compile_remoteclass, compile_remoteclass_init, compile_remoteclass_method, compile_remoteclass_del
from .proto_interface import pack_proto_function_request, pack_proto_function_response, unpack_proto_function_request, unpack_proto_function_response, pack_proto_method_request, pack_proto_method_response, unpack_proto_method_request, unpack_proto_method_response, ProtoMsg
from .grpc_interface import grpc_register_function, grpc_register_method, grpc_function_call, grpc_method_call, remote_connected
from .instance_ref import init_remoteclass, assign_ref_to_instance, del_instance

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

def function_decorator(func: Callable[P, R]) -> Callable[P, R]:
    compile_function(func)

    def function_handler(self: Any, proto_req: ProtoMsg, context: Any) -> ProtoMsg:
        args = unpack_proto_function_request(func, proto_req)
        result = func(**args) # type: ignore[call-arg]
        return pack_proto_function_response(func, result)

    grpc_register_function(func, function_handler)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if remote_connected():
            proto_req = pack_proto_function_request(func, *args, **kwargs)
            proto_res = grpc_function_call(func, proto_req)
            return cast(R, unpack_proto_function_response(func, proto_res))
        else:
            return func(*args, **kwargs)

    return wrapper

@dataclass_transform()
def dataclass_decorator(cls: Type[T]) -> Type[T]:
    datacls = dataclasses.dataclass(cls)
    compile_dataclass(datacls)
    return datacls

def method_decorator(method: Callable[P, R]) -> Callable[P, R]:
    setattr(method, "__egrpc_enabled", True)
    return method

# https://github.com/python/mypy/issues/6158
if TYPE_CHECKING:
    property_decorator = property
else:
    class property_decorator(property):
        def __init__(self,
                     fget: Callable[[Any], R],
                     fset: Optional[Callable[[Any, R], None]] = None,
                     fdel: Optional[Callable[[Any], None]]    = None,
                     fdoc: Optional[str]                      = None):
            setattr(self, "__egrpc_enabled", True)
            super().__init__(fget=fget, fset=fset)

def remoteclass_decorator(cls: Type[T]) -> Type[T]:
    init_remoteclass(cls)
    methods = {k: v for c in reversed(cls.__mro__) for k, v in c.__dict__.items() if hasattr(v, "__egrpc_enabled")}

    for method_name, method in methods.items():
        if isinstance(method, property_decorator):
            property_wrapper = register_remoteclass_property(cls, method)
            setattr(cls, method_name, property_wrapper)

        elif method_name == "__init__":
            init_wrapper = register_remoteclass_init(cls)
            setattr(cls, "__init__", init_wrapper)

        else:
            method_wrapper = register_remoteclass_method(cls, method)
            setattr(cls, method_name, method_wrapper)

    del_wrapper = register_remoteclass_del(cls)
    setattr(cls, "__del__", del_wrapper)

    compile_remoteclass(cls)

    return cls

def register_remoteclass_init(cls: Type[T]) -> Callable[..., None]:
    init_method = getattr(cls, "__init__")

    compile_remoteclass_init(cls, init_method)

    def init_handler(self: Any, proto_req: ProtoMsg, context: Any) -> ProtoMsg:
        args = unpack_proto_method_request(cls, init_method, proto_req)
        obj = cls(**args)
        return pack_proto_method_response(cls, init_method, obj)

    grpc_register_method(cls, init_method, init_handler)

    @functools.wraps(init_method)
    def init_wrapper(*args: Any, init_method: Callable[P, R] = init_method, **kwargs: Any) -> None:
        if remote_connected():
            proto_req = pack_proto_method_request(cls, init_method, *args, **kwargs)
            proto_res = grpc_method_call(cls, init_method, proto_req)
            instance_ref = unpack_proto_method_response(cls, init_method, proto_res)
            assign_ref_to_instance(cls, args[0], instance_ref)
        else:
            init_method(*args, **kwargs)

    return init_wrapper

def register_remoteclass_del(cls: Type[T]) -> Callable[..., None]:
    del_method = getattr(cls, "__del__")

    compile_remoteclass_del(cls, del_method)

    def del_handler(self: Any, proto_req: ProtoMsg, context: Any) -> ProtoMsg:
        args = unpack_proto_method_request(cls, del_method, proto_req)
        del_instance(cls, list(args.values())[0])
        return pack_proto_method_response(cls, del_method, None)

    grpc_register_method(cls, del_method, del_handler)

    @functools.wraps(del_method)
    def del_wrapper(self: Any) -> None:
        try:
            if remote_connected():
                proto_req = pack_proto_method_request(cls, del_method, self)
                grpc_method_call(cls, del_method, proto_req)
            else:
                del_method(self)
        except Exception:
            pass

    return del_wrapper

def register_remoteclass_method(cls: Type[T], method: Callable[P, R]) -> Callable[P, R]:
    compile_remoteclass_method(cls, method)

    def method_handler(self: Any, proto_req: ProtoMsg, context: Any) -> ProtoMsg:
        args = unpack_proto_method_request(cls, method, proto_req)
        result = method(**args) # type: ignore[call-arg]
        return pack_proto_method_response(cls, method, result)

    grpc_register_method(cls, method, method_handler)

    @functools.wraps(method)
    def method_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if remote_connected():
            proto_req = pack_proto_method_request(cls, method, *args, **kwargs)
            proto_res = grpc_method_call(cls, method, proto_req)
            return cast(R, unpack_proto_method_response(cls, method, proto_res))
        else:
            return method(*args, **kwargs)

    return method_wrapper

def register_remoteclass_property(cls: Type[T], prop: property_decorator) -> property:
    assert prop.fget is not None
    qualname = prop.fget.__qualname__

    if not prop.fget.__qualname__.endswith(".getter"):
        prop.fget.__qualname__ = f"{qualname}.getter"
    fget_wrapper = register_remoteclass_method(cls, prop.fget)

    if prop.fset is not None:
        if not prop.fset.__qualname__.endswith(".setter"):
            prop.fset.__qualname__ = f"{qualname}.setter"
        fset_wrapper = register_remoteclass_method(cls, prop.fset)
    else:
        fset_wrapper = None

    return property(fget=fget_wrapper, fset=fset_wrapper)
