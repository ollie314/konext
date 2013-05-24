#!/usr/bin/python
__author__ = 'mehdi'

#####################################
#                                   #
#       Protocol definition.        #
#                                   #
#####################################
#                                   #
#   version : 1                     #
#   author : mlefebvre@simnetsa.ch  #
#   copyright : Simnet S.A.         #
#                                   #
#####################################

READ = "RE"
SEND = "SE"
WATCH = "WE"
UNWATCH = "UE"
BYE = "QE"

HELO_PREFIX = "CH"
HELO_SUFFIX = ",EADP/0.1"
HELO_MIDDLE = "welcome, %s,"
HELO_PROTO = "EADP/0.1"
HELO_RESPONSE = "welcome, %s, %s"

HELO_ACK = "aH"
READ_ACK = "dE"
WATCH_ACK = "eE"
UNWATCH_ACK = WATCH_ACK
SEND_ACK = "sE"
END_ACK = "aE"
BYE_ACK = "qE"

READING_PROCESS = 'groupcacheread'
SENDING_PROCESS = 'groupsocketsend'
WATCHING_PROCESS = 'grouplisten'
UNWATCHING_PROCESS = 'grouplisten'


def get_process_for_command(command):
    return {
        READ: READING_PROCESS,
        SEND: SENDING_PROCESS,
        WATCH: WATCHING_PROCESS
    }[command]


def get_header(cmd):
    return cmd.split(" ", 1)[0]


def get_client_name(cmd):
    command_arg = cmd.split(" ", 1).pop()
    client_name = command_arg.split(",", 1)[0].strip()
    return client_name


def get_body(cmd):
    header = get_header(cmd)
    return {
        HELO_PREFIX: cmd.split(' ').pop(),
        READ: cmd.split(' ').pop(),
        SEND: cmd.split(' ').pop(),
        WATCH: cmd.split(' ').pop(),
        UNWATCH: cmd.split(' ').pop(),
        BYE: ''
    }[header]


def send_command(command, processor):
    command_header = get_header(command)
    command_body = get_body(command)
    response = processor.send_command(command_header, command_body)
    if None == response:
        return "nE E22, \"%s: Invalid argument\"\n" % command
    ack = get_ack(command_header)
    return "%s %s\n%s\n" % (ack, response, END_ACK)


def get_ack(statement):
    return {
        HELO_PREFIX: "%s %s %s" % (HELO_ACK, HELO_MIDDLE, HELO_PROTO),
        READ: READ_ACK,
        SEND: SEND_ACK,
        WATCH: WATCH_ACK,
        UNWATCH: UNWATCH_ACK,
        BYE: BYE_ACK
    }[statement]


# main programm only used for testing purpose
if __name__ == '__main__':

    print "Testing get_ack ..."
    assert get_ack(HELO_PREFIX) % "me" == get_ack(HELO_PREFIX) % "me"  # dum test ... fix later ...
    assert get_ack(READ) == READ_ACK
    assert get_ack(SEND) == SEND_ACK
    assert get_ack(WATCH) == WATCH_ACK
    assert get_ack(UNWATCH) == WATCH_ACK
    assert get_ack(BYE) == BYE_ACK
    print "Done !\n"