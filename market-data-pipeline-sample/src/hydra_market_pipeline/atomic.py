"""Atomic file replacement with collision-safe same-directory temporary files."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from typing import Any, Callable


def write_atomically(
    path: Path,
    mode: str,
    write: Callable[[Any], None],
    **open_kwargs: Any,
) -> None:
    for _ in range(100):
        temporary_path = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(
                temporary_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
                0o666,
            )
        except FileExistsError:
            continue
        break
    else:
        raise FileExistsError(f"could not allocate a temporary file for {path.name}")

    try:
        try:
            existing_stat = path.lstat()
        except FileNotFoundError:
            existing_stat = None
        if (
            os.name == "posix"
            and existing_stat is not None
            and stat.S_ISREG(existing_stat.st_mode)
        ):
            os.fchmod(descriptor, stat.S_IMODE(existing_stat.st_mode))
        with os.fdopen(descriptor, mode, **open_kwargs) as handle:
            descriptor = None
            write(handle)
        os.replace(temporary_path, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
