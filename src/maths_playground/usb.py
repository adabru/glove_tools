
import time
import serial

from .protocol import *


class USB(Protocol):
    class PackageReadBuffer:
        transmissionStartTime = 0
        data = bytearray(1024)
        offset = 0

    packageReadBuffer = PackageReadBuffer()
    packageWriteBuffer = bytearray(DataSend.SIZE)

    channel = None

    firstConnect = False

    def communicate(self):
        self.firstConnect = True
        self.connect()

    def connect(self):
        # check connection health
        # TODO, broken → serial.close()
        # TODO, channel is None or channel is not open
        if self.channel is None:
            self.channel = serial.Serial('/dev/ttyUSB0', 230400, timeout=1)
            self.channel.flushInput()
            self.channel.flushOutput()
            t0 = time.perf_counter()
        if self.firstConnect:
            self.firstConnect = False
            return True
        return False

    def memoryCompare(self, sequence, array, offset=0):
        return sequence == array[offset:offset + len(sequence)]

    def readPackage(self):
        if self.channel is None:
            raise ConnectionError('serial-channel is None')
        buffer = self.packageReadBuffer
        packetType = PacketType.NONE
        while self.channel.in_waiting > 0:
            x = self.channel.read(1)[0]
            t1 = time.perf_counter()
            # case 1: last package timed out
            if buffer.transmissionStartTime > 0 and t1 > buffer.transmissionStartTime + 2.0:
                print('timeout')
                buffer.transmissionStartTime = 0
            # case 2: transmission of new package
            if buffer.transmissionStartTime == 0:
                buffer.offset = 0
                buffer.transmissionStartTime = t1
            # case 3: buffer overflow, this package will be corrupted
            if buffer.offset == len(buffer.data):
                print('buffer overflow')
                buffer.offset = 0
            # case 4: continuation of already started package
            buffer.data[buffer.offset] = x
            buffer.offset += 1
            # case 5: end of package reached
            if buffer.offset >= len(PACKAGE_DELIM) and self.memoryCompare(PACKAGE_DELIM, buffer.data, buffer.offset - len(PACKAGE_DELIM)):
                # print(b.offset)
                packetLen = buffer.offset - len(PACKAGE_DELIM)
                buffer.transmissionStartTime = 0
                if self.memoryCompare(b'DATA', buffer.data):
                    if buffer.offset - len(PACKAGE_DELIM) != DataReceive.SIZE:
                        print(
                            'data packet has wrong size: was {} but must be {}'.format(packetLen, DataReceive.SIZE))
                        packetType = PacketType.NONE
                        break
                    else:
                        self.updateData(self.packageReadBuffer.data)
                        packetType = PacketType.DATA
                        break
                elif self.memoryCompare(b'DEBUG', buffer.data):
                    self.debugReceive = self.packageReadBuffer.data[5:packetLen].decode(
                        'utf8')
                    packetType = PacketType.DEBUG
                    break
                elif buffer.data[0] == ord('{'):
                    # glove information sent as json
                    self.updateInformation(
                        self.packageReadBuffer.data[:packetLen])
                    packetType = PacketType.INFORMATION
                    break
                else:
                    print(
                        'incomplete or unrecognized package, starts with: ' + str(buffer.data[:5]))
                packetType = PacketType.NONE
                break
        return packetType

        # {
        #     PacketType.DATA: lambda:
        #         # TODO lock(callbackLock)
        #     dataReceiveCallback(dataReceive)
        #     PacketType.INFORMATION: lambda:
        #         # TODO lock(callbackLock)
        #     informationReceiveCallback(informationReceive)
        #     PacketType.DEBUG: lambda:
        #         print('[glove debug]' + debugReceive)
        #     PacketType.NONE: lambda:}[packetType]()

    def writePackage(self):
        if self.channel is None:
            raise ConnectionError('serial-channel is None')
        self.dataSend.serialize(self.packageWriteBuffer)
        self.channel.write(self.packageWriteBuffer)
        self.channel.write(PACKAGE_DELIM)
        # clear flag
        self.dataSend.requestInformation = False
        return True

    def close(self):
        if serial is not None:
            print('Closing Serial')
            # TODO
