#!/usr/bin/python           # This is server.py file
import sys
import socket_engine
from setup import setup_config
from liblogging import init_logger
import liblogging


if __name__ == '__main__':
    config = setup_config("konext")
    port = int(config['port'])                       # Reserve a port for your service.
    address = config['server_address']          # Address to listening on
    app_name = config['app_name']               # Name of the application

    # initialize the logger
    liblogging.logger = init_logger(config['format'],
                                    app_name,
                                    config['log_file'],
                                    config['max_logfile_size'],
                                    config['nb_logfile'])

    # checking availability ...
    if not socket_engine.check_server(address, port):
        print("Port or address is busy. Please refer to logs to know more about the failure")
        sys.exit(1)     # exiting due to error ...

    socket_engine.configure_and_start_server(config)
