"""Unix advisory locks covering complete read/modify/write transactions."""
from __future__ import annotations

import fcntl
import hashlib
from contextlib import contextmanager
from functools import wraps
from pathlib import Path


@contextmanager
def locked(resource):
    resource = Path(resource).resolve()
    directory = resource.parent.parent / ".ose-locks"
    directory.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(str(resource).encode()).hexdigest() + ".lock"
    with (directory / name).open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def index_transaction(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with locked(function.__globals__["INDEX"]):
            return function(*args, **kwargs)
    return wrapped
