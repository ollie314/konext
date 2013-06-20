__author__ = 'mlefebvre'

import random
import errno
import threading
import time
import StringIO
import Queue
from tasker import Task
import libkonext
import liblogging
from socket import *        # Import socket module
from cmd_parser import Parser
from process_sender import Processor
from provider import EibdWriter, EibdWatcher


class Dispatcher(threading.Thread):
    """
    This class is responsible to manage client connection and act as a bridge between the client and the eibd
    """

    BUFF_SIZE = 1024
    DEFAULT_WATCH_QUEUE_SIZE = 1000
    DEFAULT_READ_QUEUE_SIZE = 1000
    DEFAULT_SEND_QUEUE_SIZE = 1000

    def __init__(self, client_socket, client_address, buffer_size=BUFF_SIZE, options=None):
        threading.Thread.__init__(self)             # thread initialization
        self.client_socket = client_socket          # client socket information
        self.client_address = client_address        # client address information

        self.parser = Parser()                      # define the parser for the thread
        self.processor = Processor()                # define the process launcher for the thread ...
        self.processor.set_parser(self.parser)      # ... and configure it
        self.name = "anonymous"                     # define the name of the client
        self.logged_in = False                      # tag user as not logged in (according to the protocol
        self.failed_attempt = 0                     # current number of failed response handling attempt
        self.max_failed_attempt = 10                # maximum number of failed response handling attempt

        self.options = options                      # optional configuration option
        self.buffer_size = buffer_size              # size of the buffer to read / write data from / to the socket

        self.watch_stack = []                       # stack to store watched addresses
        self.watch_stack_lock = threading.RLock()   # lock on the watch_stack
        self.watch_queue = Queue.Queue()            # queue for watching response
        self.read_queue = Queue.Queue()             # queue for reading from eibd socket
        self.write_queue = Queue.Queue()            # queue for write to eibd socket
        self.is_running = False                     # indicates if the thread is running or has been broked (idle convenience)

        # define the daemon to write on the queue
        self.writer_daemon = EibdWriter(self.write_queue, self.watch_stack_lock)

        # define the daemon to listen connection on the queue
        self.listener_daemon = EibdWatcher(self.watch_stack, self.watch_stack_lock, self.watch_queue, self.read_queue, self.client_address, self.client_socket)


    def send_back(self, message):
        self.client_socket.send(message)

    def send_back_cors(self):
        with open('/var/www/crossdomain.xml', 'r') as content_file:
            cors_resp = content_file.read()
        self.send_back(cors_resp.strip())

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

    def idle(self, stime):
        cnt = 0
        while self.is_running:
            if cnt >= stime:
                return
            cnt+=.5
            time.sleep(.5)

    def read(self):
        return self.client_socket.recv(self.buffer_size)

    def close_and_dispose(self):
        self.debug("Stopping writer daemon")
        self.debug("Stopping listener daemon")
        self.writer_daemon.stop()
        self.listener_daemon.stop()

        # TODO : create a cleanest way to do that
        # create a specific task to force thread to exit (since thread as marked as stopped they will exiting ...
        task = Task.create_task_from_raw("RE 1/1/0")
        task.group_address = '1/1/0'
        self.write_queue.put(task)

        self.writer_daemon.join(1)
        self.debug("Writer daemon stopped")

        self.listener_daemon.join(1)
        self.debug("Listener daemon stopped")

        self.debug("Disposing client connection")
        self.client_socket.close()
        self.is_running = False
        self.debug("Client connection disposed")

    def send_response_from_read_queue(self):
        """
        Not use for now since we delegate the response process to the watcher.
        :return:
        """
        return -1
        # self.log("Sending process will send_back [%s] in response to command [%s] from %s" % (response, command, self.client_address))
        # self.send_back(response)

    def manage_watch_stack(self, tasks):
        """
        Add or remove a watched address / list of addresses from the stack of watched address

        :param tasks: list of task which define the command => addresses concerned by the current job
        """
        self.watch_stack_lock.acquire()

        for task in tasks:
            group_address = task.group_address
            if group_address in self.watch_stack and task.command == libkonext.UNWATCH:
                liblogging.log("Removing address [%s] into the watch stack" % group_address, liblogging.DEBUG)
                self.watch_stack.remove(group_address)
            elif group_address not in self.watch_stack and task.command == libkonext.WATCH:
                liblogging.log("Adding address [%s] into the watch stack" % group_address, liblogging.DEBUG)
                self.watch_stack.append(group_address)
            else:
                liblogging.log("Nothing to do with the val [%s] into the watch stack" % group_address, liblogging.DEBUG)

        self.watch_stack_lock.release()

    def dispatch_task(self, task):
        """
        dispatching a task depending on his nature ...

        :param task: task to dispatch
        :return: dispatching process result (0 => OK, > 1 => KO)
        """
        process_result = 0
        tasks = Task.extract_tasks(task)

        if task.command in [libkonext.WATCH, libkonext.UNWATCH]:
            self.manage_watch_stack(tasks)

        if task.command == libkonext.UNWATCH:
            self.send_back("%s\n" % libkonext.END_ACK)
            return process_result

        for t in tasks:
            max_attempt = 10
            # in all cases, send task to the write queue ...
            while 1:
                try:
                    self.write_queue.put(t)
                    # write tasks should respond with a read, so a write tasks emmit two tasks in the request queue
                    # 1 => Write,
                    # 2 => Read
                    if t.command == libkonext.SEND:
                        clone = Task.clone_task(t)
                        clone.command = libkonext.READ
                        #self.write_queue.put(clone)
                        self.write_queue.put(clone)
                    break
                except Queue.Full:
                    max_attempt -= 1
                    if not max_attempt:
                        self.error("A task will be ignored cause too many attempt to push it into the request queue")
                        break
                    # let a chance to other thread to stack out task from the queue
                    time.sleep(1)
                except Exception, e:
                    self.error("Unexpected error occurred on the thread responsible to enqueue tasks. The task has been dropped out %s" % e.message)
                    process_result = 1
                    break

        return process_result

    def init_and_start_daemons(self):
        self.writer_daemon.setDaemon(0)
        self.listener_daemon.setDaemon(0)
        self.writer_daemon.start()
        self.listener_daemon.start()

    def run(self):
        """
        This method will run for each client. It is a thread callback,
        It means that it is executed inside a thread.

        This thread should have many references to be able to dial with the client.

        :param clientsock: Reference to the client socket
        :param addr: address of the socket.
        """
        self.init_and_start_daemons()
        self.is_running = True

        while self.is_running:

            data = self.read()
            if data.rstrip() == 'quit':     # hang off in this case
                break

            # --------------------------------------------------------- #

                            #### command validation ... ####

            # --------------------------------------------------------- #

            command = data.rstrip()

            self.debug("Receive command [%s] from %s" % (command, self.client_address))

            # manage empty data reception ...
            if data == '':
                try:
                    self.send_back("\n")
                    continue
                except IOError, ioe:
                    if ioe.errno == errno.EPIPE:
                        self.warn("Detecting a broken pipe")
                        break
                    else:
                        continue
                except Exception, e:
                    self.failed_attempt += 1
                    if self.failed_attempt > self.max_failed_attempt:
                        self.error("Detecting exceeding number of generic exception, close connection")
                        break
                    self.warn("Detecting generic exception, try continue")
                    continue

            # reset failed_attempt flag because request passed
            self.failed_attempt = 0

            #
            # try to manage cors issue created by the flash socket implementation.
            #
            if self.parser.detect_cors(command):
                self.send_back_cors()
                continue

            #
            # ensure the command validity (syntaxic validation).
            #
            # FIXME : since the behavior of the socket is a little bit unexcpected sometimes, we have to review the code to be more flexible
            #
            if not self.parser.is_valid_command(command):
                msg = "nE E22, \"%s: Invalid argument\"\n" % command
                self.warn("Invalid command [%s] received from[ %s]" % (command, self.client_address))
                self.send_back(msg)
                continue

                        #### end of command validation ... ####

            # --------------------------------------------------------- #

                            ### command parsing process ###

            # --------------------------------------------------------- #

            self.debug("Extract header for command [%s] from %s" % (command, self.client_address))
            header = libkonext.get_header(command)
            self.debug("Receive header [%s] from %s" % (header, self.client_address))

            # first, check if the login command has been sent
            if not self.logged_in and header != libkonext.HELO_PREFIX:
                self.debug("Receive a command [%s] from %s but client not logged in and command is not an helo" % (command, self.client_address))
                msg = "nE E13, \"%s: Permission denied\"\n" % command
                self.warn("Permission denied for %d, client not connected" % self.client_address)
                self.send_back(msg)
                continue

            #
            #  check if the command is a valid helo command (semantic validation)
            #
            # TODO : move this implementation in the parser / processor may be a good idea
            #
            if not self.logged_in and header == libkonext.HELO_PREFIX and not self.parser.is_valid_helo_command(command):
                self.debug("Receive a command [%s] from %s but client not logged in and command is not a valid helo" % (command, self.client_address))
                msg = "nE E22, \"%s: Invalid argument\"\n" % command
                self.warn("Invalid helo command [%s] received from[ %s]" % (command, self.client_address))
                self.send_back(msg)
                continue

                                    #### remote command processing ####

            self.debug("Process start for command [%s] from %s" % (command, self.client_address))

            # log in client
            if header == libkonext.HELO_PREFIX and not self.logged_in:
                self.debug("Connecting process is invoking for command [%s] from %s" % (command, self.client_address))
                self.name = libkonext.get_client_name(command)
                self.info("The client %s is now connected with %s" % (self.client_address, self.name))
                msg = "%s\n" % (libkonext.get_ack(header) % self.name)
                self.send_back(msg)
                self.logged_in = True
            else:
                try:
                    #
                    # TODO : manage queue processing  ...
                    #
                    self.debug("Process send the command [%s] from %s" % (command, self.client_address))

                    # manage command case ...
                    task = Task.create_task_from_raw(command)
                    self.dispatch_task(task)
                    self.send_response_from_read_queue()    # blocking process
                    continue
                except IOError, ioe:
                    self.debug("Process leave an exception [%s] for command [%s] from %s" % (e.message, command, self.client_address))
                    msg = "nE E22, \"%s: Invalid argument\"\n" % command
                    self.warn("Invalid command [%s] received from[ %s] is sending back to the client socket" % (command, self.client_address))
                    self.send_back(msg)
                    pass
                except:
                    self.debug("Process leave an exception [%s] for command [%s] from %s" % (e.message, command, self.client_address))
                    msg = "nE E22, \"%s: Invalid argument\"\n" % command
                    self.warn("Invalid command [%s] received from[ %s] is sending back to the client socket" % (command, self.client_address))
                    self.send_back(msg)
                    pass

            # try:
            #     msg = "%s\n" % (libkonext.get_ack(header) % name)
            # except TypeError:
            #     msg = "%s\n" % libkonext.get_ack(header)
            #
            # self.client_socket.send(msg)

        # --------------------------------------------------------- #

                            #### Connection closing ####

        # --------------------------------------------------------- #

        try:
            self.debug("Closing connection for (%s,%s)" % self.client_address)
            msg = "%s %s\n" % (libkonext.get_header(libkonext.BYE_ACK), self.name)
            self.close_and_dispose()
            self.log("Connection closed from (%s,%s)." % self.client_address)
        except IOError, e:
            if e.errno == errno.EPIPE:
                self.error("Client hang up")
            else:
                self.error("mysterious IO exception handled [IOError : %s]" % e.message)
            pass
        else:
            self.error("mysterious exception handled, no more information")

                          #### End of connection closing ####