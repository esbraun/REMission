"""One Linux process-shared gate; no PID/file-existence lock approximation."""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import threading
import time


class AdmissionError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


_registry_lock = threading.Lock()
_mutexes = {}


class AdmissionGate:
    def __init__(self, database, *, timeout=5):
        if sys.platform != 'linux':
            raise AdmissionError('unsupported_live_hold_platform')
        self.database = Path(database).resolve(strict=True)
        if Path(database).is_symlink() or self.database.stat().st_nlink != 1:
            raise AdmissionError('unsupported_database_alias')
        self.path = Path(str(self.database) + '.admission.lock')
        if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_nlink != 1:
            raise AdmissionError('invalid_admission_lock')
        self.timeout = timeout
        identity = (self.path.stat().st_dev, self.path.stat().st_ino)
        with _registry_lock:
            self.mutex = _mutexes.setdefault(identity, threading.Lock())

    @contextmanager
    def hold(self):
        import fcntl
        deadline = time.monotonic() + self.timeout
        if not self.mutex.acquire(timeout=self.timeout):
            raise AdmissionError('safety_admission_busy')
        descriptor = None
        try:
            descriptor = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW)
            opened, current = os.fstat(descriptor), self.path.stat()
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise AdmissionError('invalid_admission_lock')
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise AdmissionError('safety_admission_busy')
                    # Poll lock availability only; tests determine winners with barriers.
                    time.sleep(min(.01, max(0, deadline-time.monotonic())))
            yield
        finally:
            if descriptor is not None:
                os.close(descriptor)  # OS releases ownership even on process death.
            self.mutex.release()
