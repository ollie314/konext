from unicodedata import category
from tasker import Task
from cmd_parser import Parser
import Dpt_Types
import re
import time
import threading
import Queue
import libkonext
import liblogging
import EIBConnection
import warnings

class EibdWriter(threading.Thread):

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

    def __init__(self, queue, watch_stack_lock, eibd_addr='ip:127.0.0.1', parser=None):
        threading.Thread.__init__(self)
        self.queue = queue
        self.watch_stack_lock = watch_stack_lock

        self.queue_wait_time = 0.0
        self.dpt = Dpt_Types.dpt_type(self)

        # may be use for parsing, but normally, the parser should do the job
        self.AddrRegex = re.compile(r"(?:|(\d+)[\x2F|\x2E])(\d+)[\x2F|\x2E](\d+)$", re.MULTILINE)

        #self.eibmutex = threading.RLock()  # no longer use due to queue management implementation

        self.eibd_address = eibd_addr
        self.command = None
        self.eibd_connection = None
        self.connected = False
        self.is_running = False
        if parser is None:
            self.parser = Parser()
        else:
            self.parser = parser

    # --------------------------------------------------------- #

                        #### logging commands ####

    # --------------------------------------------------------- #

    # TODO refactor the logging methods to use a more common / convenient way
    def log(self, message, level=liblogging.INFO):
        liblogging.log(message, level)

    def debug(self, message):
        self.log(message, liblogging.DEBUG)

    def info(self, message):
        self.log(message)

    def warn(self, message):
        self.log(message, liblogging.WARNING)

    def error(self, message):
        self.log(message, liblogging.ERROR)

    def critical(self, message):
        self.log(message, liblogging.CRITICAL)

    def fatal(self, message):
        self.log(message, liblogging.FATAL)

    # --------------------------------------------------------- #

    def connect(self, eibd_address='ip:127.0.0.1'):
        self.eibd_connection = EIBConnection.EIBConnection()
        self.remote_socket = self.eibd_connection.EIBSocketURL(eibd_address)
        self.connected = True

    def disconnect(self):
        self.eibd_connection.EIBClose()
        self.remote_socket = None
        self.eibd_connection = None
        self.connected = False

    def send_write(self, address, value, flag=0x80):
        if not self.connected:
            self.connect()

        self.eibd_connection.EIBOpen_GroupSocket(0)
        _address = self.parser.read_group_address(address)
        _value = self.parser.read_hex(value)

        apdu = [0, flag]

        if type(_value) == int:
            apdu.append(_value)
        elif type(value) == list:
            apdu = apdu + _value
        else:
            msg = "invalid Message  %r to %r" % (value, address)
            self.error(msg)
            raise Exception(msg)

        self.debug("Sending write order ...")
        resp = self.eibd_connection.EIBSendGroup(_address, apdu)
        self.debug("Write order sent !")
        self.last_data = self.eibd_connection.data
        return resp

    def send_read(self, address, flag=0x00):
        if not self.connected:
            self.connect()
        self.eibd_connection.EIBOpen_GroupSocket(0)
        _address = self.parser.read_group_address(address)
        apdu = [flag] * 2
        self.debug("Sending read order ...")
        resp = self.eibd_connection.EIBSendGroup(_address, apdu)
        self.debug("Read order sent !")

        self.last_data = self.eibd_connection.data
        self.debug("data %s" % self.last_data)
        return resp

    def stop(self):
        self.is_running = False

    def run(self):
        self.info("Running the watcher")
        self.is_running = True
        while self.is_running:
            try:
                self.debug("Trying to extract something from the queue")
                task = self.queue.get()
            except Queue.Empty, qe:
                self.debug("Attempt to fetch something from the queue failed due to empty queue, sleeping for 1 sec. [%s]" % qe.message)
                time.sleep(1)
                pass
            except BaseException:
                self.info("Generic error occurred in the request queue processor, but ignoring it ")
                pass
            else:
                self.debug("Starting a new task for the task [%s]" % task.uuid)
                # do the task.
                # TODO : if the task is too old, skip it and log information about the case
                if task.kind in [Task.READ_TASK, libkonext.KNX_READ_FLAG, libkonext.WATCH, libkonext.KNX_RESPONSE_FLAG]:
                    self.send_read(task.group_address)
                else:
                    self.send_write(task.group_address, task.value)

                self.queue.task_done()
                self.debug("Task [%s] sent to eibd" % task.uuid)

        self.debug("Write thread ended, closing connection")
        self.disconnect()
        self.debug("Write thread is now disposed")


class EibdWatcher(threading.Thread):
    """
    Watch the eibd queue and send back response to the client
    """

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

    def __init__(self, watch_stack, watch_stack_lock, watch_queue, response_queue, client_address, client_socket):
        """
        Watching process to handle response from the bus and forward these on the client socket stream

        :param watch_stack: List of address watched
        :param watch_stack_lock: Lock on the address watched
        :param watch_queue: Queue of address watched to send back to the client (deprecated)
        :param response_queue:queue of response to send back to the client (deprecated)
        :param client_address: client socket address reference
        :param client_socket: client socket reference
        """
        threading.Thread.__init__(self)
        self.parser = Parser()
        self.watch_stack = watch_stack              # list of address watched
        self.watch_stack_lock = watch_stack_lock    # lock on the watch address list to share this between threads
        self.watch_queue = watch_queue              # queue of watching response to send back to the client socket
        self.response_queue = response_queue        # queue of response to send back to the client socket
        self.client_address = client_address        # client address for socket communication
        self.client_socket = client_socket          # client socket reference
        self.cache_ok = False                       # Flag to indicate cache status (activated or not) - deprecated
        self.eibd_connection = None                 # Eibd connection reference
        self.remote_socket = None                   # Eibd socket connection reference
        self.connected = False                      # Flag to indicate EIBD connection status
        self.buff = None                            # Buffer to deal with eibd data
        self.src = None                             # Source address for eibd transaction (data exchange)
        self.dest = None                            # Destination address for eibd transaction (data exchange)
        self.parser = Parser()                      # Reference to the parser to use to parse information (translation)
        self.is_running = False                     # Flag to indicate if the thread is running or if it has to be stop

    # --------------------------------------------------------- #

                        #### logging commands ####

    # --------------------------------------------------------- #

    # TODO refactor the logging methods to use a more common / convenient way
    def log(self, message, level=liblogging.INFO):
        liblogging.log(message, level)

    def debug(self, message):
        self.log(message, liblogging.DEBUG)

    def info(self, message):
        self.log(message)

    def warn(self, message):
        self.log(message, liblogging.WARNING)

    def error(self, message):
        self.log(message, liblogging.ERROR)

    def critical(self, message):
        self.log(message, liblogging.CRITICAL)

    def fatal(self, message):
        self.log(message, liblogging.FATAL)

    # --------------------------------------------------------- #

    def connect(self, eibd_address='ip:127.0.0.1'):
        self.eibd_connection = EIBConnection.EIBConnection()
        self.remote_socket = self.eibd_connection.EIBSocketURL(eibd_address)
        self.connected = True

    def disconnect(self):
        self.eibd_connection.EIBClose()
        self.remote_socket = None
        self.eibd_connection = None
        self.connected = False

    def init_cache(self):
        """
        Initialize cache reading options
        """
        warnings.warn("Cache is now deprecated in init_cache", category=DeprecationWarning)
        self.debug("Eibd listener trying to intialize")
        if not self.cache_ok:
            self.debug("Cache opening is required")
            self.eibd_connection.EIB_Cache_Enable()
            self.cache_ok = True
            self.debug("Cache successfully opened")
        else:
            self.debug("Cache already opened, skip process")

    def init_data(self):
        """
        Initialize data to use with the connection
        """
        self.debug("Eibd listener intializing data (buffer, source and destination) to handle information published on the eibd connection")
        self.buff = EIBConnection.EIBBuffer()
        self.src = EIBConnection.EIBAddr()
        self.dest = EIBConnection.EIBAddr()
        self.debug("Eibd listener successfully initialized data (buffer, source and destination)")

    def open_connection(self):
        self.debug("Eibd listener opening connection")
        if self.eibd_connection is None:
            self.connect()
        self.eibd_connection.EIBOpen_GroupSocket_async(0)
        self.debug("Eibd listener successfully opened connection")

    def send_back(self, message):
        self.client_socket.send(message)

    def is_watched_address(self, addr):
        self.watch_stack_lock.acquire()
        if addr in self.watch_stack:
            result = True
        else:
            result = False
        self.watch_stack_lock.release()
        return result

    def try_to_sendback_to_watchers(self, resp_kind, physical_address, group_address, resp_val_str):
        if not self.is_watched_address(group_address):
            return True
        try:
            header_ack = libkonext.get_ack(libkonext.READ)
            response_body = "%s=%s" % (group_address, resp_val_str)
            message = "%s %s\n" % (header_ack, response_body)
            self.send_back(message)
            return True
        except BaseException:
            self.error("Eibd listener genreic exception.")
            return False

    def send_back_response(self, resp_kind, physical_address, group_address, resp_val_str):
        try:
            header_ack = libkonext.get_ack(libkonext.READ)
            response_body = "%s=%s" % (group_address, resp_val_str)
            end_of_command = libkonext.END_ACK
            message = "%s %s\n%s\n" % (header_ack, response_body, end_of_command)
            self.send_back(message)
            return True
        except BaseException:
            self.error("Eibd listener genreic exception.")
            return False

    def prepare_and_send_response(self, resp_kind, raw_response):
        try:
            self.debug("Eibd listener process to dispatch command (response or write handled).")
            # do response processing ...
            physical_address = self.parser._decode_physical_addr(self.src.data)
            self.debug("Eibd listener : source (physical address) of the packet is %s." % physical_address)
            group_address = self.parser._decode_group_addr(self.dest.data)
            self.debug("Eibd listener : destination (group address) of the packet is %s." % group_address)
            resp_val_str = self.parser.format_result(raw_response)
            self.debug("Eibd listener : response value associate to the packet is %s." % resp_val_str)
            r = self.send_back_response(resp_kind, physical_address, group_address, resp_val_str)
            if not r:
                self.error("Error occurred during sending back the response to the client socket")
                return False
            r = self.try_to_sendback_to_watchers(resp_kind, physical_address, group_address, resp_val_str)
            if not r:
                self.error("Error occurred during sending back the watching response to the client socket")
                return False
            self.debug("Response successfully managed by the process")
            return True
        except BaseException:
            self.error("Eibd listener genreic exception.")
            return False

    def stop(self):
        self.is_running = False

    def run(self):
        self.info("Eibd listener starting ...")
        self.open_connection()
        self.init_cache()
        self.init_data()
        self.info("Eibd listener configuration process sucessfully made")
        self.is_running = True

        while self.is_running:
            self.info("Eibd listener waiting for information")
            resp_len = self.eibd_connection.EIBGetGroup_Src(self.buff, self.src, self.dest)
            resp = self.buff.buffer
            self.info("Eibd listener handling incoming information")

            if resp_len == -1:
                self.critical("Eibd listener failed to read incoming data")
            elif resp_len < 2:
                self.error("Eibd listener handling an invalid packet")
            elif resp[0] & 0x3 or (resp[1] & 0xC0) == 0xC0:
                self.error("Eibd listener handling an unknown APDU")
            else:
                self.debug("Eibd listener handling a valid packet, dispatching it.")
                # manage response type
                resp_kind = resp[1] & 0xC0
                if resp_kind == self.KNX_READ_FLAG:
                    # read is ignored by the process since it doesn't require an action...
                    self.debug("Eibd listener handling a read datagram, ignoring it.")
                elif resp_kind == self.KNX_RESPONSE_FLAG or resp_kind == self.KNX_WRITE_FLAG:
                    if resp_kind == self.KNX_WRITE_FLAG:
                        self.debug("Eibd listener handling a write datagram.")
                    else:
                        self.debug("Eibd listener handling a response datagram.")

                    proc_result = self.prepare_and_send_response(resp_kind, resp)
                    if not proc_result:
                        self.debug("Eibd listener handling an error during sending back information to the client socket")
                    else:
                        self.debug("Eibd listener successgfully handling and manage request.")
                else:
                    self.warn("Eibd listener : Unknown datagram handled")

        self.info("Eibd listener Exit from the listening thread")
        self.disconnect()
        # TODO : dispose all resources from the current object to be able to reinit it later without redundant call
        self.info("Eibd listener disconnected from the KNX Bus")