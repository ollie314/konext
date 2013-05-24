__author__ = 'mehdi'
import re


GENERAL_CMD_REGEX = "^[A-Z]{2}\s.+$"
HELO_CMD_REGEX = "^[A-Z]{2}\s\w+?,\s?EADP\/0\.1$"
READ_CMD_REGEX = "^[A-Z]{2}\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"
SEND_CMD_REGEX = "^[A-Z]{2}\s\d{1,3}(?:\/\d{1,3}){0,2}=[A-Za-z0-9]+(?:,\d{1,3}(?:\/\d{1,3}){0,2}=[A-Za-z0-9]+)*$"
WATCH_CMD_REGEX = "^[A-Z]{2}\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"
UNWATCH_CMD_REGEX = "^[A-Z]{2}\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"


class Parser:
    def __init__(self):
        self.general_cmd = re.compile(GENERAL_CMD_REGEX)
        self.helo_cmd = re.compile(HELO_CMD_REGEX)
        self.read_cmd = re.compile(READ_CMD_REGEX)
        self.send_cmd = re.compile(SEND_CMD_REGEX)
        self.watch_cmd = re.compile(WATCH_CMD_REGEX)
        self.unwatch_cmd = re.compile(UNWATCH_CMD_REGEX)

    def call(self, func, cmd):
        if func == 'is_valid_command':
            return self.is_valid_command(cmd)
        if func == 'is_valid_helo_command':
            return self.is_valid_helo_command(cmd)
        if func == 'is_valid_read_command':
            return self.is_valid_read_command(cmd)
        if func == 'is_valid_send_command':
            return self.is_valid_send_command(cmd)
        if func == 'is_valid_watch_command':
            return self.is_valid_watch_command(cmd)
        if func == 'is_valid_unwatch_command':
            return self.is_valid_unwatch_command(cmd)

        return False

    def is_valid_command(self, command):
        match = self.general_cmd.match(command)
        if match:
            return True
        return False

    def is_valid_helo_command(self, command):
        match = self.helo_cmd.match(command)
        if match:
            return True
        return False

    def is_valid_read_command(self, command):
        match = self.read_cmd.match(command)
        if match:
            return True
        return False

    def is_valid_send_command(self, command):
        match = self.send_cmd.match(command)
        if match:
            return True
        return False

    def is_valid_watch_command(self, command):
        match = self.watch_cmd.match(command)
        if match:
            return True
        return False

    def is_valid_unwatch_command(self, command):
        match = self.unwatch_cmd.match(command)
        if match:
            return True
        return False

# main programm only used for testing purpose
if __name__ == '__main__':
    parser = Parser()
    right_commands = {
        'helo': ['CH me, EADP/0.1'],
        'read': ['RE 15/0/1', 'RE 15/0/1,15/0/2,15/0/3'],
        'send': ['SE 15/0/1=FF', 'SE 15/0/1=FF,15/0/2=11,15/0/3=44'],
        'watch': ['WE 15/0/1', 'WE 15/0/1,15/0/2'],
        'unwatch': ['UE 15/0/3', 'UE 15/0/1,15/0/2']
    }

    def functions(k):
        return {
            'helo': 'is_valid_helo_command',
            'read': 'is_valid_read_command',
            'send': 'is_valid_send_command',
            'watch': 'is_valid_watch_command',
            'unwatch': 'is_valid_unwatch_command',
        }[k]

    for k, val in right_commands.items():
        func = functions(k)
        for cmd in val:
            print "Testing if the command [%s] is a valid command" % cmd
            assert True == parser.is_valid_command(cmd)
            print "OK"
            print "testing if command [%s] is valid accros function [%s] ..." % (cmd, func)
            assert True == parser.call(func, cmd)
            print "OK"

    print "Tests successfully passed"