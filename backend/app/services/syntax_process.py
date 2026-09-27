"""Reuse an isolated parser across files without giving up per-file limits."""
from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

MAX_REQUESTS = 128
PARSE_TIMEOUT = 10.0
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class SyntaxFailure(ValueError):
    pass


class SyntaxProcess:
    def __init__(self):
        self.process = None
        self.requests = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None
        self.requests = 0

    def parse(self, payload, check_cancel=lambda: None):
        if self.requests >= MAX_REQUESTS:
            self.close()
        if self.process is None:
            self.process = subprocess.Popen(
                [sys.executable, '-I', str(Path(__file__).with_name('syntax_worker.py')), '--persistent'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            os.set_blocking(self.process.stdin.fileno(), False)
            os.set_blocking(self.process.stdout.fileno(), False)
        process = self.process
        request = (json.dumps(payload, ensure_ascii=True) + '\n').encode()
        offset = 0
        output = bytearray()
        deadline = time.monotonic() + PARSE_TIMEOUT
        try:
            # Nonblocking writes also bound startup/stalled-child time for large inputs.
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdin, selectors.EVENT_WRITE)
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    check_cancel()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired('syntax_worker', PARSE_TIMEOUT)
                    for key, _ in selector.select(min(remaining, 0.1)):
                        if key.fileobj is process.stdin:
                            offset += os.write(process.stdin.fileno(), request[offset:offset + 65536])
                            if offset == len(request):
                                selector.unregister(process.stdin)
                        else:
                            chunk = os.read(process.stdout.fileno(), 65536)
                            if not chunk:
                                raise ValueError('Parser exited before producing a result.')
                            output.extend(chunk)
                            if len(output) > MAX_RESPONSE_BYTES:
                                raise ValueError('Parser response exceeds its resource budget.')
                            if output.endswith(b'\n'):
                                result = json.loads(output)
                                if isinstance(result, dict) and result.get('error'):
                                    raise SyntaxFailure('Syntax extraction failed.')
                                if not isinstance(result, dict) or result.get('path') != payload['path']:
                                    raise ValueError('Parser did not return a valid file result.')
                                self.requests += 1
                                return result
        except SyntaxFailure:
            self.requests += 1
            raise
        except BaseException:
            self.close()
            raise


class SyntaxPool:
    """Two isolated parsers per import; at most four across both import slots."""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='grepo-parse')
        self.local = threading.local()
        self.processes = []
        self.lock = threading.Lock()
        self.stopped = threading.Event()

    def __enter__(self):
        return self

    def submit(self, payload, check_cancel):
        def parse():
            def check():
                if self.stopped.is_set():
                    raise RuntimeError('Parser pool closed.')
                check_cancel()
            if not hasattr(self.local, 'parser'):
                self.local.parser = SyntaxProcess()
                with self.lock:
                    self.processes.append(self.local.parser)
            return self.local.parser.parse(payload, check)
        return self.executor.submit(parse)

    def __exit__(self, *_):
        self.stopped.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
        for parser in self.processes:
            parser.close()
