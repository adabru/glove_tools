import queue
import sys
from typing import Generator

import sounddevice as sd


class Microphone:
    def __init__(self, samplerate=16000):
        self.q: queue.Queue[bytes] = queue.Queue()
        self.samplerate = samplerate

    def callback(self, indata, frames, time, status) -> None:
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def record(self, blocksize=8000) -> Generator[bytes, None, None]:
        """
        Generator function that yields audio data chunks from the default input device.
        """
        with sd.RawInputStream(
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            callback=self.callback,
            samplerate=self.samplerate,
        ):
            while True:
                data = self.q.get()
                yield data
