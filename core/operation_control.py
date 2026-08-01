import threading


class OperationCancelled(RuntimeError):
    pass


class CancellationToken:
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        if self.is_cancelled():
            raise OperationCancelled("操作已取消")
