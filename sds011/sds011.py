"""
Copyright 2016, Frank Heuer, Germany

This file is part of SDS011.

SDS011 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SDS011 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SDS011.  If not, see <http://www.gnu.org/licenses/>.

Diese Datei ist Teil von SDS011.

SDS011 ist Freie Software: Sie können es unter den Bedingungen
der GNU General Public License, wie von der Free Software Foundation,
Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren
veröffentlichten Version, weiterverbreiten und/oder modifizieren.

SDS011 wird in der Hoffnung, dass es nützlich sein wird, aber
OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
Siehe die GNU General Public License für weitere Details.

Sie sollten eine Kopie der GNU General Public License zusammen mit SDS011
erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.
"""

"""
Modul contains the SDS011 class for controlling the sds011 particle sensor
"""
from enum import IntEnum
import logging
import time
import struct
import serial
import sds011exceptions as ex



class SDS011(object):
    """Class representing the SD011 dust sensor and its methods.
        device_path on Win is one of your COM ports, on Linux
        one of "/dev/ttyUSB..." or "/dev/ttyAMA...".
    """

    '''
    The bytes coded here are special bytes one can find in the serial communication.
    Each serial message starts with 0xAA and ends with 0xAB.
    If the message will be send to the senor, the second byte is 0xB4, the 16th and 17th
    byte is 0xFF.
    If it is a response of the sensor of a message sent before, the second byte of the response
    is 0xC5. If its a response send automatic by the sensor in "Initiative" Report Mode,
    the second byte is 0xC0.
    The third byte is always the command byte except in response to a request command or a sensor
    initiated response (second byte 0xC0).
    So a message to the senor might look this way to set Report Mode:
    Report Mode:
    ------------------------
    Setting to Initiative:
    Message  aa:b4:02:01:00:00:00:00:00:00:00:00:00:00:00:ff:ff:01:ab
    Response aa:c5:02:01:00:00:cc:0b:da:ab

    Setting to Passive:
    Message  aa:b4:02:01:01:00:00:00:00:00:00:00:00:00:00:ff:ff:02:ab
    Response aa:c5:02:01:01:00:cc:0b:db:ab

    '''
    logging.getLogger(__name__).addHandler(logging.NullHandler())

    __SerialStart = 0xAA
    __SerialEnd = 0xAB
    __SendByte = 0xB4
    __ResponseByte = 0xC5
    __ReceiveByte = 0xC0
    __ResponseLength = 10
    __CommandLength = 19
    __CommandTerminator = 0xFF

    class Command(IntEnum):
        """Enumeration of commands, the SDS011 can understand."""
        ReportMode = 2,
        Request = 4,
        DeviceId = 5,
        WorkState = 6,
        Firmware = 7,
        DutyCycle = 8

    class CommandMode(IntEnum):
        """One command can get the corrent configuration of the senor or set it"""
        Getting = 0,
        Setting = 1

    class ReportModes(IntEnum):
        '''Report modes, the sensor can run in. In passive mode one has to send a
        request command, to get the measured values as a response.'''
        Initiative = 0,
        Passiv = 1

    class WorkStates(IntEnum):
        '''Work states, the sensor can have. In sleeping mode it does not send any data.
        To get data you have to wake it up'''
        Sleeping = 0,
        Measuring = 1
    # Constructor

    def __init__(self, device_path):
        '''
        device_path on Win is one of your COM ports, on Linux
        one of "/dev/ttyUSB..." or "/dev/ttyAMA...".
        '''
        logging.debug("Start of constructor")
        self.device = serial.Serial(device_path,
                                    baudrate=9600,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE,
                                    bytesize=serial.EIGHTBITS,
                                    timeout=2)
        if self.device.isOpen() is False:
            self.device.open()
        logging.info("Communication to device at %s initiated.", device_path)

        # ToDo: initiate whith the values, the senor has. sensor has to be
        # queried for that
        self.__firmware = None
        self.__reportmode = None
        self.__workstate = None
        self.__dutycycle = None
        self.__device_id = None
        self.__read_timeout = 0
        self.__dutycycle_start = time.time()
        self.__read_timeout_drift_percent = 2
        # within response the __device_id will be set
        first_response = self.__response()
        if len(first_response) == 0:
            # Device might be sleeping. So wake it up
            logging.warning("Constructing the instance of a yet not responding "
                            "sensor. Who set it sleeping, in passive mode or a "
                            "duty cycle? I'm going to wake it up!'")
            self.__send(self.Command.WorkState,
                        self.__construct_data(self.CommandMode.Setting,
                                              self.WorkStates.Measuring))
        # at this point, device is awake, shure. So store this state
        self.__workstate = self.WorkStates.Measuring
        self.__get_current_config()
        logging.info("Sensor has firmware %s", self.__firmware)
        logging.info("Sensor is in reportmode %s", self.__reportmode)
        logging.info("Sensor is in workstate %s", self.__workstate)
        logging.info("Sensor is in dutycycle %s, None if Zero",
                     self.__dutycycle)
        logging.info("Sensor has Device ID: %s", self.device_id)
        logging.debug("Constructor successful executed.")

    # Destructor
    def __del__(self):
        # it's better to clean up
        if self.device is not None:
            self.device.close()

    # ReportMode
    @property
    def reportmode(self):
        """The reportmode, the sensor has at the moment"""
        return self.__reportmode

    @reportmode.setter
    def reportmode(self, value):
        '''Setter for reportmode. Use self.ReportMode IntEnum'''
        if (isinstance(value, self.ReportModes) or
                value is None):
            self.__send(self.Command.ReportMode, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__reportmode = value
            logging.info("reportmode set: %s", value)
        else:
            raise TypeError("reportmode must be of type SDS011.ReportModes")

    # workstate
    @property
    def workstate(self):
        """The worstate of the sensor as a value of type self.WorkStates"""
        return self.__workstate

    @workstate.setter
    def workstate(self, value):
        if (isinstance(value, self.WorkStates) or
                value is None):
            self.__send(self.Command.WorkState, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__workstate = value
            logging.info("workstate set: %s", value)
        else:
            raise TypeError("ReportMode must be of type SDS011.WorkStates")
    # dutycycle

    @property
    def dutycycle(self):
        """The dutycycle the sensor has as a value of type int"""
        return self.__dutycycle

    @dutycycle.setter
    def dutycycle(self, value):

        if (isinstance(value, int) or
                value is None):
            if value < 0 or value > 30:
                raise ValueError(
                    "dutycycle has to be between 0 and 30 inclusive!")
            self.__send(self.Command.DutyCycle, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__dutycycle = value
            # Calculate new timeout value
            self.__read_timeout = self.__calculate_read_timeout(value)
            self.__dutycycle_start = time.time()
            logging.debug("New timeout for dutycycle = %s", self.__read_timeout)
            logging.info("dutycycle set: %s", value)
            self.__get_current_config()
        else:
            raise TypeError("dutycycle must be of type SDS011.DutyCycles")

    @property
    def device_id(self):
        """The device id as a string"""
        return "{0:02x}{1:02x}".format(self.__device_id[0], self.__device_id[1]).upper()

    @property
    def firmware(self):
        """The firmware the device has"""
        return self.__firmware

    def __construct_data(self, cmdmode, cmdvalue):
        '''construct a data bytearray from cmdmode and cmdvalue.
        cmdvalue has to be self.CommandMode type and cmdvalue int
        returns bytearry of lenth 2'''
        if not isinstance(cmdmode, self.CommandMode):
            raise TypeError(
                "cmdmode must be of type {0}", type(self.CommandMode))
        if not isinstance(cmdvalue, int):
            raise TypeError("cmdvalue must be of type {0}", type(int))
        retval = bytearray()
        retval.append(cmdmode)
        retval.append(cmdvalue)
        logging.debug("Data %s for commandmode %s constructed.",
                      cmdvalue, cmdmode)
        return retval

    def __get_current_config(self):
        '''Get's the senors status at construction time of this instance
        to reflect the real status of the physical senor.'''
        # Getting the Dutycycle
        response = self.__send(self.Command.DutyCycle,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:

            dutycycle = response[1]
            self.__dutycycle = dutycycle
            self.__read_timeout = self.__calculate_read_timeout(dutycycle)
            self.__dutycycle_start = time.time()
        else:
            raise ex.GetStatusError("dutycycle not detectable")

        # Getting reportmode
        response = self.__send(self.Command.ReportMode,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:
            reportmode = self.ReportModes(response[1])
            self.__reportmode = reportmode
        else:
            raise ex.GetStatusError("reportmode not detectable")

        # Getting firmware
        response = self.__send(self.Command.Firmware,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:
            self.__firmware = "{0:02d}{1:02d}{2:02d}".format(
                response[0], response[1], response[2])
        else:
            raise ex.GetStatusError("firmware not detectable")

    def __calculate_read_timeout(self, timeoutvalue):
        newtimeout = 60 * timeoutvalue + \
            self.__read_timeout_drift_percent / 100 * 60 * timeoutvalue
        logging.info("Timeout calculated for %s is %s",
                     timeoutvalue, newtimeout)
        return newtimeout

    def get_values(self):
        '''gets the sensor response and returns measured value of pm10 and pm25'''
        logging.info("get_values entered")
        if self.__workstate == self.WorkStates.Sleeping:
            raise ex.WorkStateError("sensor is sleeping and will not " +
                                    "send any values. Wake it up first.")
        if self.__reportmode == self.ReportModes.Passiv:
            raise ex.ReportModeError("sensor is in passive report mode "
                                     "and will not automaticly send values. "
                                     "You have to call Request() to get values.")

        while self.dutycycle == 0 or \
                time.time() < self.__dutycycle_start + self.__read_timeout:
            response_data = self.__response()
            logging.debug(
                "values received from sensor with response %s.", response_data)
            return self.__extract_values_from_response(response_data)
        raise TimeoutError(
            "No data within read timeout of %s received", self.__read_timeout)

    def request(self):
        """Requests measured data as a tuple from sensor when its in ReporMode.Passiv"""
        response = self.__send(self.Command.Request, bytearray())
        retval = self.__extract_values_from_response(response)
        return retval

    def __extract_values_from_response(self, response_data):
        """extracts the value of pm25 and pm10 from sensor response"""
        data = response_data[2:6]
        value_of_2point5micro = None
        value_of_10micro = None
        if len(data) == 4:
            value_of_2point5micro = float(data[0] + (data[1] << 8)) / 10.0
            value_of_10micro      = float(data[2] + (data[3] << 8)) / 10.0
            logging.debug("get_values successful executed.")
            if self.dutycycle != 0:
                self.__dutycycle_start = time.time()
            return (value_of_10micro, value_of_2point5micro)
        elif self.dutycycle == 0:
            raise ValueError("Data is missing")

    def __send(self, command, data):
        '''method for sending commands to the sensor and returning the response'''
        logging.debug("send() entered with command %s and data %s.",
                      command.name, data)
        # Proof the input
        if not isinstance(command, self.Command):
            raise TypeError("command must be of type SDS011.Command")
        if not isinstance(data, bytearray):
            raise TypeError("data must be of type bytearray")
        logging.debug("Input parameter proofed")
        # Initialise the commandarray
        bytes_to_send = bytearray()
        bytes_to_send.append(self.__SerialStart)
        bytes_to_send.append(self.__SendByte)
        bytes_to_send.append(command.value)
        # Add data and set zero to rest
        for i in range(0, 12):
            if i < len(data):
                bytes_to_send.append(data[i])
            else:
                bytes_to_send.append(0)
        # last two bytes before the checksum are CommandTerminator
        bytes_to_send.append(self.__CommandTerminator)
        bytes_to_send.append(self.__CommandTerminator)
        # calculate the checksum
        checksum = self.__checksum_make(bytes_to_send)
        # append checksum
        bytes_to_send.append(checksum % 256)
        # and append terminator for serial send
        bytes_to_send.append(self.__SerialEnd)

        #LOGGER.debug("Going to send: %s", "".join("%02x:" % b for b in bytes_to_send))
        logging.debug("Going to send: %s", bytes_to_send)

        # send the command
        written_bytes = self.device.write(bytes_to_send)
        self.device.flush()
        if written_bytes != len(bytes_to_send):
            raise IOError("Not all bytes written")
        logging.debug("Sent and flushed: %s", bytes_to_send)
        # proof the receive value
        received = self.__response(command)
        logging.debug("Received: %s", received)

        if len(received) == 0:
            raise ValueError("nothing received")

        # when no command or command is request command,
        # second byte has to be ReceiveByte
        if ((command is None or command == self.Command.Request) and
                received[1] != self.__ReceiveByte):
            raise ValueError(
                "expected receive value {0:#X} for value request \
                or polling not found. Actual:{1}".format(self.__ReceiveByte, received[1]))

        # check, if response is response of the command, except Command.Request
        if command is not self.Command.Request:
            if received[2] != command.value:
                raise ValueError(
                    "expected receive value for value command not found")
            else:
                returnvalue = received[3: -2]
        else:
            returnvalue = received
        # return just the received data. Further evaluation of data outside of
        # this function
        logging.debug("Leaving send() normal and returning %s", received[3: -2])
        return returnvalue

    def __response(self, command=None):
        '''gets and proofs the response from the senor. Response can be
        the response of a sent command or just the measured date while sensor
        is in reportmode Initiative'''
        # receive the response while listening serial input
        bytes_received = bytearray(1)
        one_byte = bytes(0)
        while True:
            one_byte = self.device.read(1)
            '''if no bytes are read sensor might be in sleep mode.
            It makes no sense to raise an exception here. raise condition
            should be proofed in a context outside this fuction'''
            if len(one_byte) > 0:
                bytes_received[0] = ord(one_byte)
                # if this is true, serial data is comming
                if bytes_received[0] == self.__SerialStart:
                    single_byte = self.device.read(1)
                    if (((command is not None and command != self.Command.Request)
                         and ord(single_byte) == self.__ResponseByte) or
                            ((command is None or command is self.Command.Request)
                             and ord(single_byte) == self.__ReceiveByte)):
                        bytes_received.append(ord(single_byte))
                        break
            else:
                if self.__dutycycle == 0:
                    logging.error("A sensor response has not arrived within timeout limit. "
                                  "Is the senor in sleeping mode. Wake it up first! Returning "
                                  "empty bytearray from response!")
                else:
                    logging.debug("No response as expected while in dutycycle")
                return bytearray()

        thebytes = struct.unpack('BBBBBBBB', self.device.read(8))
        bytes_received.extend(thebytes)
        if command is not None and command is not self.Command.Request:
            if bytes_received[1] is not self.__ResponseByte:
                raise IOError("ResponseByte not found in serial data")
            if bytes_received[2] != command.value:
                raise IOError(
                    "Third byte of serial data {0} received is not belonging \
                    to prior sent command {1}".format(bytes_received[2], command.name))

        if command is None or command is self.Command.Request:
            if bytes_received[1] is not self.__ReceiveByte:
                raise IOError("Received byte not found for Value Request")

        # proof checksum
        if self.__checksum_make(bytes_received[0:-2]) != bytes_received[-2]:
            raise IOError("Checksum of received data not valid")

        # set device_id if device Id is None, proof it, if it's not None
        if self.__device_id is None:
            self.__device_id = bytes_received[-4:-2]
        elif self.__device_id is not None and not self.__device_id.__eq__(bytes_received[-4:-2]):
            raise ValueError("Data received (%s) are from device and do not belong "
                             "to this device with id %s.",
                             bytes_received, bytes_received[-4:-2], self.__device_id)
        logging.debug("response() successful run")
        return bytes_received

    def __checksum_make(self, data):
        '''
        Generates the checksum for data to send or data recieved from sensor.
        data has to be of type bytearray and must start with 0xAA at first
        and (0xB4 or 0xC5 or 0xC0) at second position. It must end before
        the position where the checksum has to be placed.
        '''
        logging.debug("Building checksum for data %s.", data)
        # Build checksum for data to send or receive
        if len(data) not in (self.__CommandLength - 2, self.__ResponseLength - 2):
            raise ValueError("data has to be {0} or {1} long".format(
                self.__CommandLength - 2, self.__ResponseLength))
        if data[0] != self.__SerialStart:
            raise ValueError("Data is missing startbit")
        if data[1] not in (self.__SendByte, self.__ResponseByte, self.__ReceiveByte):
            raise ValueError(
                "Data is missing SendBit-, ReceiveBit- or ReceiveValue-Byte")
        if data[1] != self.__ReceiveByte and data[2] not in list(map(int, self.Command)):
            raise ValueError(
                "data's command byte value {0} is not valid".format(data[2]))
        #checksum = command.value + bytes_to_send[15] + bytes_to_send[16]
        checksum = 0
        for i in range(2, len(data)):
            checksum = checksum + data[i]
        checksum = checksum % 256
        logging.debug("Checksum calculated is %s.", checksum)
        return checksum
