import pickle
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from ..ui.settings import *
from ..ui.util import *


class _MockSocket:
    def listen(self):
        pass

    def accept(self):
        pass

    def receive(self, timeout):
        return pickle.dumps((0, (0, 0), (0, 0), (0, 0), (0, 0)))

    def close_connection(self):
        pass


sock_gaze = _MockSocket()

# for debugging
# from graph import *

# graph = Graph()


@dataclass
class InputFrame:
    # timestamp
    t: float
    # eye position relative to tracker [mm]
    l0: np.ndarray
    r0: np.ndarray
    # gaze destination relative to tracker [mm]
    l1: np.ndarray
    r1: np.ndarray

    @staticmethod
    def from_bytes(transmission: bytes) -> "InputFrame":
        t, l0, l1, r0, r1 = pickle.loads(transmission)
        return InputFrame(t, vec(l0), vec(r0), vec(l1), vec(r1))


class GazeThread(QThread):
    gaze_signal = Signal(object)

    def __init__(self, pause_lock):
        super().__init__()
        self.pause_lock = pause_lock

        # for debugging
        # graph.setup()

    def run(self):
        sock_gaze.listen()
        while True:
            print("Wait for a connection")
            sock_gaze.accept()
            print("Connected. Listening for keys ...")
            try:
                # Receive the data in small chunks and retransmit it
                while True:
                    self.pause_lock.lock()
                    self.pause_lock.unlock()
                    transmission = sock_gaze.receive(2.0)
                    gaze_frame = InputFrame.from_bytes(transmission)
                    self.gaze_signal.emit(gaze_frame)
                    # graph.gaze_signal.emit(t, l0, l1, r0, r1)

            except (
                ValueError,
                RuntimeError,
                pickle.UnpicklingError,
                TimeoutError,
            ) as err:
                print(err)

            finally:
                print("Clean up the connection")
                sock_gaze.close_connection()
