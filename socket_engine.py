__author__ = 'mehdi'

import libkonext
import liblogging
from socket import *        # Import socket module
import thread
from cmd_parser import Parser
from process_sender import Processor


# checking port to be sure it is empty ...
def check_server(address, port):
    """

    :param address: address to check
    :param port: port to connect to
    :return: true if address is ready to use false otherwise
    """
    s = socket()
    liblogging.log("Checking local on port [%s:%d]" % (address, port), liblogging.INFO)
    try:
        s.connect((address, port))
        # we are able to connect on this port, it means that a server already listening on it ... cannot start the server
        liblogging.log(
            "Failure port [%s:%d] is not ready [error : %s]" % (address, port, 'Already listen on the requested port'), liblogging.INFO)
        return False
    except error, e:
        liblogging.log("OK local port [%s:%d] is ready to use" % (address, port), liblogging.INFO)
        return True


# handler to execute in the thread
def handler(client_socket, client_address, buffer_size=102):
    """

    :param clientsock:
    :param addr:
    """

    parser =  Parser()
    processor = Processor()
    name = "anonymous"
    logged_in = False

    while 1:
        data = client_socket.recv(buffer_size)
        if not data or data.rstrip() == 'quit':
            break

        command = data.rstrip()
        liblogging.log("Receive command [%s] from %s" % (command, client_address), liblogging.DEBUG)
        if not parser.is_valid_command(command):
            msg = "nE E22, \"%s: Invalid argument\"\n" % command
            liblogging.log("Invalid command [%s] received from[ %s]" % (command, client_address), liblogging.WARNING)
            client_socket.send(msg)
            continue

        header = libkonext.get_header(command)
        liblogging.log("Receive header [%s] from %s" % (header, client_address), liblogging.DEBUG)

        # first, check if the login command has been sent
        if not logged_in and header != libkonext.HELO_PREFIX:
            msg = "nE E13, \"%s: Permission denied\"\n" % command
            liblogging.log("Permission denied for %s, client not connected" % client_address, liblogging.WARNING)
            client_socket.send(msg)
            continue

        # check if the command is a valid helo command
        if not logged_in and header == libkonext.HELO_PREFIX and not parser.is_valid_helo_command(command):
            msg = "nE E22, \"%s: Invalid argument\"\n" % command
            liblogging.log("Invalid helo command [%s] received from[ %s]" % (command, client_address), liblogging.WARNING)
            client_socket.send(msg)
            continue

        # log in client
        if header == libkonext.HELO_PREFIX:
            name = libkonext.get_client_name(command)
            liblogging.log("The client %s is now connected with %s" % (client_address, name), liblogging.INFO)
            msg = "%s\n" % (libkonext.get_ack(header) % name)
            client_socket.send(msg)
            logged_in = True
        else:
            try:
                # manage command case ...
                response = libkonext.send_command(command, processor)
                client_socket.send(response)
                continue
            except Exception:
                msg = "nE E22, \"%s: Invalid argument\"\n" % command
                liblogging.log("Invalid command [%s] received from[ %s]" % (command, client_address), liblogging.WARNING)
                client_socket.send(msg)

        # try:
        #     msg = "%s\n" % (libkonext.get_ack(header) % name)
        # except TypeError:
        #     msg = "%s\n" % libkonext.get_ack(header)
        #
        # client_socket.send(msg)

    header = libkonext.get_header(libkonext.BYE_ACK)
    msg = "%s %s\n" %(header, name)
    client_socket.send(msg)
    client_socket.close()

    liblogging.log("Connection closed from (%s,%s)." % client_address)


def configure_and_start_server(config):

    s = socket()                                    # Create a socket object
    host = gethostname()                            # Get local machine name
    s.bind((host, int(config['port'])))             # Bind to the port
    buffer_size = int(config['buffer_size'])             # sizing the buffer for reading from socket
    max_connection = int(config['max_connection'])  # define the max concurrent connection supported by the server

    s.listen(max_connection)      # Now wait for client connection.
    liblogging.log("Server is now waiting for connection", liblogging.INFO)
    while True:
        c, addr = s.accept()     # Establish connection with client.
        liblogging.log("Got connection from (%s, %s)" % addr)
        c.send("cE %s\n" % config['msg_banner'])
        thread.start_new_thread(handler, (c, addr, buffer_size))
        # c.close()                # Close the connection