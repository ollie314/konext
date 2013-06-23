#!/usr/bin/python
# This is server.py file
import os
import sys
import socket_engine
from setup import setup_config, mark_pid_on_fs
from liblogging import init_logger
import liblogging
from flashpolicyd import policy_server


if __name__ == '__main__':

    print "Trying to start the flash policy daemon"
    policy_server(843, './flashpolicy.xml').run()

    config = setup_config("konext")
    port = int(config['port'])                  # Port to listening on
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
        liblogging.log("Port or address is busy. Please refer to logs to know more about the failure", liblogging.ERROR)
        sys.exit(1)     # exiting due to error ...

    mark_pid_on_fs()
    liblogging.log("Server starting with pid [%d]" % os.getpid())
    socket_engine.configure_and_start_server(config)
