# egrpc (eazy gRPC)

egrpc is a Python framework for transparent inter-process communication over gRPC.
It generates protobuf definitions and gRPC services automatically from Python type hints at import time, eliminating the need for `.proto` files or manual code generation.
Just add decorators and your functions and classes become callable across process boundaries.

## Installation

```bash
pip install egrpc
```

## Usage

### Remote functions

`@egrpc.function` makes a function callable over gRPC.
Arguments and return values are serialized automatically based on type hints.

```python
import egrpc

@egrpc.function
def add(x: int, y: int) -> int:
    return x + y
```

Supported types include `int`, `float`, `str`, `bool`, `None`, `list`, `dict`, `tuple`, `Union`, `Optional`, `slice`, and nested combinations.

### Dataclasses

`@egrpc.dataclass` defines a value type that is passed by value (serialized by field) across the RPC boundary.

```python
@egrpc.dataclass
class Point:
    x: float
    y: float

@egrpc.function
def distance(p1: Point, p2: Point) -> float:
    return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5
```

### Remote classes

`@egrpc.remoteclass` defines a stateful object that lives on the server.
The client holds a lightweight reference and calls methods via gRPC.

```python
@egrpc.remoteclass
class Counter:
    @egrpc.method
    def __init__(self, initial: int = 0):
        self._count = initial

    @egrpc.property
    def count(self) -> int:
        return self._count

    @egrpc.method
    def increment(self) -> None:
        self._count += 1
```

### Server / Client

Server:

```python
egrpc.serve(port=12345)
```

Client:

```python
egrpc.connect("localhost", 12345)

print(add(1, 2))  # 3
print(distance(Point(0, 0), Point(3, 4)))  # 5.0

c = Counter(10)
c.increment()
print(c.count)  # 11

egrpc.disconnect()
```

## Development

This project is managed using uv.

Test:
```sh
uv run pytest
```

Type check:
```sh
uv run mypy --strict src/ test/
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 TOYOTA MOTOR CORPORATION.
