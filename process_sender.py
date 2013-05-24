#! /usr/bin/env python
__author__ = 'mlefebvre'
import EIBConnection


class Processor:
    
    READ_COMMAND_HEADER = "RE"
    SEND_COMMAND_HEADER = "SE"
    WATCH_COMMAND_HEADER = "WE"
    UNWATCH_COMMAND_HEADER = "UE"
    
    READ_COMMAND_CODE = 0x1
    SEND_COMMAND_CODE = 0x2
    WATCH_COMMAND_CODE = 0x3
    UNWATCH_COMMAND_CODE = 0x4

    def __init__(self, eibd_addr='127.0.0.1'):
        """

        :param eibd_addr: address of the eibd server
        """
        self.eibd_address = eibd_addr
        self.command = None
        self.eibd_connection = None
        self.connected = False

    def is_connected(self):
        return self.connected

    def connect(self):
        # self.eibd_connection = EIBConnection()
        # self.remote_socket = self.eibd_connection.EIBSocketURL(self.eibd_address)
        self.connected = True

    def disconnect(self):
        # self.eibd_connection.EIBClose()
        # self.remote_socket = None
        # self.eibd_connection = None
        self.connected = False

    def __get_code(self, header):
        return {
            self.READ_COMMAND_HEADER: self.READ_COMMAND_CODE,
            self.SEND_COMMAND_HEADER: self.SEND_COMMAND_CODE,
            self.WATCH_COMMAND_HEADER: self.WATCH_COMMAND_CODE,
            self.UNWATCH_COMMAND_HEADER: self.UNWATCH_COMMAND_CODE
        }[header]

    def send_command(self, header, body):
        code = self.__get_code(header)
        if code == self.READ_COMMAND_CODE:
            return "%s=FF" % body
        return None


if __name__ == '__main__':
    processor = Processor
    print(Processor.READ_COMMAND_CODE)
    print "OK"