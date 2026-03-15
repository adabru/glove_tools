
# see CynteractGlove.ino

import struct
import json
import re

from panda3d.core import LQuaternionf


class PacketType:
    NONE = 0
    DATA = 1
    INFORMATION = 2
    DEBUG = 3


PACKAGE_DELIM = b'CYNTERACT\n'


class IMUData:
    x = 0
    y = 0
    z = 0
    w = 1


class DataReceive:
    FMT = '=4s' + 'h' * 8 + 'f' * 4 * 16 + 'b' * 16 + 'b' * 10 + 'xx'
    SIZE = struct.calcsize(FMT)
    header = b'DATA'
    # One value per force sensor, in the range[0, 1023].
    force = [0] * 8  # short
    # One quaternion per imu sensor, the values are in the range[-1.0, 1.0].
    imu = [IMUData() for i in range(0, 16)]  # 4 floats
    # composite of: bb calibration profile nvs status ~ bb calibration status ~ bbbb system status
    imuStatus = [0] * 16  # byte
    # status of vibration feedback
    vibStatus = [0] * 10  # byte

    def deserialize(self, buffer):
        fields = struct.unpack_from(DataReceive.FMT, buffer)
        (self.header,
         self.force[0], self.force[1], self.force[2], self.force[3], self.force[4], self.force[5], self.force[6], self.force[7],
         self.imu[0].x, self.imu[0].y, self.imu[0].z, self.imu[0].w,
         self.imu[1].x, self.imu[1].y, self.imu[1].z, self.imu[1].w,
         self.imu[2].x, self.imu[2].y, self.imu[2].z, self.imu[2].w,
         self.imu[3].x, self.imu[3].y, self.imu[3].z, self.imu[3].w,
         self.imu[4].x, self.imu[4].y, self.imu[4].z, self.imu[4].w,
         self.imu[5].x, self.imu[5].y, self.imu[5].z, self.imu[5].w,
         self.imu[6].x, self.imu[6].y, self.imu[6].z, self.imu[6].w,
         self.imu[7].x, self.imu[7].y, self.imu[7].z, self.imu[7].w,
         self.imu[8].x, self.imu[8].y, self.imu[8].z, self.imu[8].w,
         self.imu[9].x, self.imu[9].y, self.imu[9].z, self.imu[9].w,
         self.imu[10].x, self.imu[10].y, self.imu[10].z, self.imu[10].w,
         self.imu[11].x, self.imu[11].y, self.imu[11].z, self.imu[11].w,
         self.imu[12].x, self.imu[12].y, self.imu[12].z, self.imu[12].w,
         self.imu[13].x, self.imu[13].y, self.imu[13].z, self.imu[13].w,
         self.imu[14].x, self.imu[14].y, self.imu[14].z, self.imu[14].w,
         self.imu[15].x, self.imu[15].y, self.imu[15].z, self.imu[15].w,
         self.imuStatus[0], self.imuStatus[1], self.imuStatus[2], self.imuStatus[3],
         self.imuStatus[4], self.imuStatus[5], self.imuStatus[6], self.imuStatus[7],
         self.imuStatus[8], self.imuStatus[9], self.imuStatus[10], self.imuStatus[11],
         self.imuStatus[12], self.imuStatus[13], self.imuStatus[14], self.imuStatus[15],
         self.vibStatus[0], self.vibStatus[1], self.vibStatus[2], self.vibStatus[3],
         self.vibStatus[4], self.vibStatus[5], self.vibStatus[6], self.vibStatus[7],
         self.vibStatus[8], self.vibStatus[9],
         ) = fields


# Packet format that is sent to the glove to change vibration strength or to request information on the glove.
class DataSend:
    FMT = '=4s' + 'b' * 10 + 'b' * 10 + 'b'
    SIZE = struct.calcsize(FMT)
    header = b'DATA'
    # Set the vibration strength of the vibration motors, accepted value range is [0, 100].
    vibration = [0] * 10  # byte
    # Set the vibration pattern of the vibration motors.
    vibrationPattern = [0] * 10  # byte
    # Boolean flag to request more glove information.
    requestInformation = False

    def serialize(self, buffer):
        struct.pack_into(self.FMT, buffer, 0, self.header,
                         self.vibration[0], self.vibration[1], self.vibration[2], self.vibration[3], self.vibration[4],
                         self.vibration[5], self.vibration[6], self.vibration[7], self.vibration[8], self.vibration[9],
                         self.vibrationPattern[0], self.vibrationPattern[1], self.vibrationPattern[
                             2], self.vibrationPattern[3], self.vibrationPattern[4],
                         self.vibrationPattern[5], self.vibrationPattern[6], self.vibrationPattern[
                             7], self.vibrationPattern[8], self.vibrationPattern[9],
                         self.requestInformation)


class Protocol:
    """Base-class for glove interfaces. Provides access to all data that was sent from the glove.
    Takes care of sensor mapping. Override this class with interface specific classes."""

    # Struct that must be populated and is sent when sendData() is called.
    dataSend = DataSend()
    # Struct that is used to deserialize received data.
    _dataReceiveBuffer = DataReceive()
    # Dictionary with parsed data. It is updated when receivePackage() returns PacketType.Data.
    dataReceive = None
    # String that is updated when a call to receivePackage() returns PacketType.Debug.
    debugReceive = ''
    # JSON-String derived dictionary that is updated when a call to receivePackage() returns PacketType.Information.
    informationReceive = None
    # The dictionary to map IMUs from received data to their names
    imuMapping = {}

    def updateInformation(self, package):
        """Parses the bytes that were sent from the glove. Includes quote-reinsertion and json parsing. Furthermore stores the dict."""
        message = package.decode('utf8')
        jsonString = re.sub(r'([\w]+)', r'"\1"', message)
        parsed = json.loads(jsonString)
        self.informationReceive = parsed
        # update imu dictionary
        for index in parsed['IMU']:
            self.imuMapping[parsed['IMU'][index]] = int(index)

    def updateData(self, package):
        self._dataReceiveBuffer.deserialize(package)
        if self.informationReceive:
            self.dataReceive = {
                'rawQuats': {},
                'imuStatus': {}
            }
            for name in self.imuMapping:
                imuData = self._dataReceiveBuffer.imu[self.imuMapping[name]]
                imuStatus = self._dataReceiveBuffer.imuStatus[self.imuMapping[name]]
                self.dataReceive['rawQuats'][name] = LQuaternionf(
                    imuData.x, imuData.y, imuData.z, imuData.w)
                self.dataReceive['imuStatus'][name] = imuStatus

    def connect(self):
        raise NotImplementedError(self.__class__.__name__ + '.connect')

    def close(self):
        raise NotImplementedError(self.__class__.__name__ + '.close')

    def writePackage(self):
        raise NotImplementedError(self.__class__.__name__ + '.writePackage')

    def readPackage(self):
        raise NotImplementedError(self.__class__.__name__ + '.readPackage')
