from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

try:
    from core.operation_control import CancellationToken, OperationCancelled
except ModuleNotFoundError:
    from stm32_git_release_tool.core.operation_control import CancellationToken, OperationCancelled


class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()


class TaskWorker(QRunnable):
    def __init__(self, task, *args, controlled=False, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.controlled = controlled
        self.cancel_token = CancellationToken()
        self.signals = WorkerSignals()

    def cancel(self):
        self.cancel_token.cancel()

    @pyqtSlot()
    def run(self):
        try:
            if self.controlled:
                result = self.task(
                    self.cancel_token,
                    self.signals.progress.emit,
                    *self.args,
                    **self.kwargs,
                )
            else:
                result = self.task(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except OperationCancelled:
            self.signals.cancelled.emit()
        except Exception as exc:
            self.signals.error.emit(str(exc))
