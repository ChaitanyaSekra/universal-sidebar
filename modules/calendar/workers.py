"""
modules/calendar/workers.py

Every Google Calendar call (auth flow, list/create/update/delete) hits the
network and can take anywhere from milliseconds to several seconds (or
hang on a slow connection). Running these directly on the Qt main thread
would freeze the whole sidebar -- including unrelated modules -- for the
duration of the call. Each worker below runs one operation on a QThread
and reports back via signals, which Qt safely marshals onto the main
thread for us.
"""

from PySide6.QtCore import QThread, Signal


class _BaseWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 -- surface any failure to the UI
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


def run_async(fn, on_success, on_error, *args, **kwargs) -> _BaseWorker:
    """Fire-and-forget helper: runs fn(*args, **kwargs) on a background
    thread, calls on_success(result) or on_error(message) on the main
    thread when done. Caller must keep a reference to the returned worker
    alive until it finishes (Qt threads get garbage collected mid-run
    otherwise) -- view.py stores it on self.
    """
    worker = _BaseWorker(fn, *args, **kwargs)
    worker.succeeded.connect(on_success)
    worker.failed.connect(on_error)
    worker.start()
    return worker
