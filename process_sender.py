#! /usr/bin/env python
__author__ = 'mlefebvre'

import sys
import signal
import os
import re
from Queue import Empty, Full, Queue, PriorityQueue
import GroupSocket
import heapq
import threading
import time
import parser
import EIBConnection
import Dpt_Types
from liblogging import log, DEBUG, INFO, ERROR, CRITICAL, FATAL, WARNING


class Processor:
    
    READ_COMMAND_HEADER = "RE"
    SEND_COMMAND_HEADER = "SE"
    WATCH_COMMAND_HEADER = "WE"
    UNWATCH_COMMAND_HEADER = "UE"
    
    READ_COMMAND_CODE = 0x1
    SEND_COMMAND_CODE = 0x2
    WATCH_COMMAND_CODE = 0x3
    UNWATCH_COMMAND_CODE = 0x4

    KNX_READ_FLAG = 0x00
    KNX_RESPONSE_FLAG = 0x40
    KNX_WRITE_FLAG = 0x80

    def __init__(self, eibd_addr='ip:127.0.0.1', parser=None):
        """

        :param eibd_addr: address of the eibd server
        """
        self.eibd_address = eibd_addr
        self.command = None
        self.eibd_connection = None
        self.connected = False
        self.parser = parser

        self.eibmutex = threading.RLock()
        self.proc_list = {}
        self.proc_list_lock = threading.RLock()
        #self.send_queue = KNXSendQueue(maxsize=1000) # define a queue with 1000 datagram as up limit
        self.queue_wait_time = 0.0
        self.group_socket = GroupSocket.groupsocket(False)
        self.dpt = Dpt_Types.dpt_type(self)

        # may be use for parsing, but normally, the parser should do the job
        self.AddrRegex = re.compile(r"(?:|(\d+)[\x2F|\x2E])(\d+)[\x2F|\x2E](\d+)$", re.MULTILINE)

        #define threads
        self._read_thread = threading.Thread()
        self._send_thread = threading.Thread()
        self._check_thread = threading.Thread()

        self.last_data = None
        self.cache_ok = False

        self.watch_initialized = False
        self.buff = None
        self.src = None
        self.dest = None

    def set_parser(self, parser):
        self.parser = parser

    def is_connected(self):
        return self.connected

    def connect(self):
        self.eibd_connection = EIBConnection.EIBConnection()
        self.remote_socket = self.eibd_connection.EIBSocketURL(self.eibd_address)
        self.connected = True

    def disconnect(self):
        self.eibd_connection.EIBClose()
        self.remote_socket = None
        self.eibd_connection = None
        self.connected = False

    def __get_code(self, header):
        return {
            self.READ_COMMAND_HEADER: self.READ_COMMAND_CODE,
            self.SEND_COMMAND_HEADER: self.SEND_COMMAND_CODE,
            self.WATCH_COMMAND_HEADER: self.WATCH_COMMAND_CODE,
            self.UNWATCH_COMMAND_HEADER: self.UNWATCH_COMMAND_CODE
        }[header]

    def send_command(self, header, body):
        log("Trying to send a command from the processor [header:%s, body:%s]" % (header, body), DEBUG)
        code = self.__get_code(header)
        log("Code is [%s]" % code, DEBUG)
        if code == self.READ_COMMAND_CODE:
            log("Return a read command with value FF", DEBUG)
            return "%s=FF" % body
        log("Unsupported code [%s] for now" % code, WARNING)
        return None

    def read(self, address, flag=0x0):
        self.eibd_connection.EIBOpen_GroupSocket(0)

        _address = self.parser.read_group_address(address)

        # Arrange the APDU according to the protocol
        apdu = [flag] * 2

        print "Sending read order ..."
        resp = self.eibd_connection.EIBSendGroup(_address, apdu)
        print "Read order sent !"

        self.last_data = self.eibd_connection.data
        print "data %s" % self.last_data

        return resp

    def init_watcher(self):
        log("Initialize EIBD listening process EIBOpen_GroupSocket_async", DEBUG)
        self.eibd_connection.EIBOpen_GroupSocket_async(0)

        #
        # Forget the cache processing for now, it was a test
        #
        #if not self.cache_ok:
            # self.eibd_connection.EIB_Cache_Enable()
        #    self.cache_ok = True

        log("Initialize EIBD buffer", DEBUG)
        self.buff = EIBConnection.EIBBuffer()
        log("EIBD buffer initialized", DEBUG)
        log("Initialize EIBD src addr", DEBUG)
        self.src = EIBConnection.EIBAddr()
        log("EIBD src addr initialized", DEBUG)
        log("Initialize EIBD dest addr", DEBUG)
        self.dest = EIBConnection.EIBAddr()
        log("EIBD dest addr initialized", DEBUG)
        self.watch_initialized = True

    def watch(self):
        resp_len = self.eibd_connection.EIBGetGroup_Src(self.buff, self.src, self.dest)
        resp = self.buff.buffer

        if resp_len == -1:
            log("Read failed", CRITICAL)
        elif resp_len < 2:
            log("Ivalid packet", ERROR)
        elif resp[0] & 0x3 or (resp[1] & 0xC0) == 0xC0:
            log("Unknown APDU received", ERROR)
        else:
            # manage response type
            resp_kind = resp[1] & 0xC0
            if resp_kind == self.KNX_READ_FLAG:
                # read ...
                log("Read datagram handled", INFO)
            elif resp_kind == self.KNX_RESPONSE_FLAG or resp_kind == self.KNX_WRITE_FLAG:
                if resp_kind == self.KNX_WRITE_FLAG:
                    log("Write datagram handled", INFO)
                else:
                    log("Response datagram handled", INFO)

                # do response processing ...
                physical_address = self.parser._decode_physical_addr(self.src.data)
                print "addr phy %s" % physical_address
                group_address = self.parser._decode_group_addr(self.dest.data)
                print "addr group %s" % group_address
                #response_val = None
                resp_str = self.parser.format_result(resp)
                print "Response is : %s" % resp_str
            else:
                log("Unknown datagram handled", WARNING)

        return resp

    def write(self, address, value, flag=0x80):
        self.eibd_connection.EIBOpen_GroupSocket(0)
        _address = parser.read_group_address(address)
        _value = parser.read_hex(value)
        if _value == 0x0:
            buff_size = 1
        else:
            buff_size = 2
        apdu = [0, flag]
        if type(_value) == int:
            apdu.append(_value)
        elif type(value) == list:
            apdu = apdu + _value
        else:
            raise Exception("invalid Message  %r to %r" % (value, address))

        print "Sending write order ..."
        resp = self.eibd_connection.EIBSendGroup(_address, apdu)
        print "Write order sent !"
        self.last_data = self.eibd_connection.data
        return resp


class KNXSendQueue(Queue):
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = []
        self.activeaddr = []

    def _qsize(self):
        return len(self.queue)

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Check whether the queue is full
    def _full(self):
        return self.maxsize > 0 and len(self.queue) == self.maxsize

    # Put a new item in the queue
    def _put(self, item):
        ## add addr to active addr
        addr = item[0]
        item += time.time(),
        prio = 0
        if len(self.queue) > 10:
            ## if queue size is over 10 use priority
            prio = int(self.activeaddr.count(addr) > 5)
        self.activeaddr.append(addr)
        heapq.heappush(self.queue,(prio,item))

    # Get an item from the queue
    def _get(self):
        prio,item = heapq.heappop(self.queue)
        addr = item[0]
        self.activeaddr.remove(addr)
        return item


class Spy(threading.Thread):

    def __init__(self, processor=None):
        super(Spy, self).__init__()
        if processor is None:
            self.processor = Processor("ip:127.0.0.1", Parser())
        else:
            self.processor = processor

        self._stop = threading.Event()
        # signal.signal(signal.SIGQUIT, self.sigquit_hdlr)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def sigquit_hdlr(self):
        print "Quit handled"
        self.stop()
        self.join(2)

    def run(self):
        self.processor.connect()
        self.processor.init_watcher()
        while True:
            resp = self.processor.watch()
            print "Response received : %s" % resp
        self.processor.disconnect()

if __name__ == '__main__':
    import sys
    from cmd_parser import Parser
    parser = Parser()
    processor = Processor("ip:127.0.0.1", parser)
    addr = sys.argv[1]
    val = sys.argv[2]
    #addr = '15/0/2'
    #val = '00'
    print 'Connecting'
    try:
        processor.connect()

        spy = Spy()
        spy.start()

        _len = processor.write(addr, val)
        print "Len written is %d" % _len
        print "Eibd data : %s\n" % processor.last_data
        processor.disconnect()
        processor.connect()
        read_val = processor.read(addr)
        print "Read data is %d" % read_val
        print "Eibd data : %s\n" % processor.last_data

        print "Waiting for spy"

        spy.join()
        processor.disconnect()

        print 'OK'

    except Exception, e:
        print 'Connection failed. Reason [%s]' % e