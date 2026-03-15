import os

from PySide6.QtCore import QThread, Signal

from .settings import *


class HotḱeyThread(QThread):
    hotkey_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        FIFO = Sockets.eyeput

        try:
            os.unlink(FIFO)
        except OSError:
            if os.path.exists(FIFO):
                raise

        os.mkfifo(FIFO)

        while True:
            with open(FIFO) as fifo:
                data = fifo.read()
                if len(data) > 0:
                    self.hotkey_signal.emit(data)
