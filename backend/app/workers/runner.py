"""Background execution of processing jobs on a bounded thread pool."""
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BackgroundRunner:
    def __init__(self, max_workers: int = 4, synchronous: bool = False) -> None:
        self.synchronous = synchronous
        self._pool = None if synchronous else ThreadPoolExecutor(max_workers=max_workers,
                                                                 thread_name_prefix="balagh-job")
        self._futures: set[Future[Any]] = set()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if self._pool is None:
            fn(*args, **kwargs)
            return
        future = self._pool.submit(fn, *args, **kwargs)
        self._futures.add(future)
        future.add_done_callback(self._done)

    def _done(self, future: Future[Any]) -> None:
        self._futures.discard(future)
        exc = future.exception()
        if exc:
            logger.error("Background job crashed: %r", exc)

    def wait_idle(self, timeout: float | None = None) -> None:
        for future in list(self._futures):
            future.result(timeout=timeout)

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
