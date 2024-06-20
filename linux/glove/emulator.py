
import pickle
import time

from .protocol import *


class Emulator(Protocol):
    def __init__(self, commToRecord=None):
        super().__init__()
        if commToRecord == None:
            self.inst = _PlaybackInstance(self)
        else:
            self.inst = _RecordingInstance(self, commToRecord)

    def connect(self):
        return self.inst.connect()

    def writePackage(self):
        return self.inst.writePackage()

    def readPackage(self):
        return self.inst.readPackage()

    def close(self):
        return self.inst.close()


class _RecordingInstance(Protocol):
    def __init__(self, parent, commToRecord):
        super().__init__()
        self.parent = parent
        self.commToRecord = commToRecord

    def connect(self):
        self.tape = []
        self.t0 = time.perf_counter()
        self.commToRecord.connect()

    def writePackage(self):
        self.commToRecord.writePackage()

    def readPackage(self):
        type = self.commToRecord.readPackage()
        object = None
        if type == PacketType.DATA:
            object = self.commToRecord.dataReceive
            self.parent.dataReceive = object
        elif type == PacketType.DEBUG:
            object = self.commToRecord.debugReceive
            self.parent.debugReceive = object
        elif type == PacketType.INFORMATION:
            object = self.commToRecord.informationReceive
            self.parent.informationReceive = object
        if object != None:
            self.tape.append({
                'time': time.perf_counter() - self.t0,
                'type': type,
                'object': object
            })
        return type

    def close(self):
        with open('recording.pickle', 'wb') as f:
            pickle.dump(self.tape, f)
        self.commToRecord.close()


class _PlaybackInstance(Protocol):
    isPaused = False
    pauseTime = 0

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def togglePause(self):
        # also pause playback time
        if not self.isPaused:
            self.pauseTime = time.perf_counter()
        else:
            self.t0 += time.perf_counter() - self.pauseTime
        self.isPaused = not self.isPaused

    def connect(self):
        with open('recording.pickle', 'rb') as f:
            self.tape = pickle.load(f)
        self.t0 = time.perf_counter()

    def writePackage(self):
        pass

    def readPackage(self):
        if not self.isPaused and len(self.tape) > 0 and time.perf_counter() - self.t0 >= self.tape[0]['time']:
            item = self.tape.pop(0)
            if item['type'] == PacketType.INFORMATION:
                self.parent.informationReceive = item['object']
            elif item['type'] == PacketType.DEBUG:
                self.parent.debugReceive = item['object']
            elif item['type'] == PacketType.DATA:
                self.parent.dataReceive = item['object']
            return item['type']
        else:
            return PacketType.NONE

    def close(self):
        pass
