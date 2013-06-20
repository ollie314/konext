__author__ = 'mehdi'
import re
from liblogging import log, DEBUG, INFO, CRITICAL, FATAL, WARNING


GENERAL_CMD_REGEX = "^[A-Z]{2}\s.+$"
HELO_CMD_REGEX = "^[A-Z]{2}\s\w+?,\s?EADP\/0\.1$"
READ_CMD_REGEX = "^RE\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"
SEND_CMD_REGEX = "^SE\s\d{1,3}(?:\/\d{1,3}){0,2}=[A-Za-z0-9]+(?:,\d{1,3}(?:\/\d{1,3}){0,2}=[A-Za-z0-9]+)*$"
WATCH_CMD_REGEX = "^WE\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"
UNWATCH_CMD_REGEX = "^UE\s\d{1,3}(?:\/\d{1,3}){0,2}(?:,\d{1,3}(?:\/\d{1,3}){0,2})*$"
G_ADDR_REGEX = "^(\d{1,3})(?:(?:\/(\d{1,3}))(?:\/(\d{1,3}))?)?$"

CORS_REGEX = "^\<.*\>"


class Parser:

    KNXREADFLAG = 0x00
    KNXRESPONSEFLAG = 0x40
    KNXWRITEFLAG = 0x80

    def __init__(self):
        self.general_cmd = re.compile(GENERAL_CMD_REGEX)
        self.helo_cmd = re.compile(HELO_CMD_REGEX)
        self.read_cmd = re.compile(READ_CMD_REGEX)
        self.send_cmd = re.compile(SEND_CMD_REGEX)
        self.watch_cmd = re.compile(WATCH_CMD_REGEX)
        self.unwatch_cmd = re.compile(UNWATCH_CMD_REGEX)
        self.g_addr = re.compile(G_ADDR_REGEX)
        self.cors_regex = re.compile(CORS_REGEX)

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

    def detect_cors(self, command):
        # <policy-file-request/>
        match = self.cors_regex.match(command)
        if match:
            return True
        return False


    def is_valid_command(self, command):
        log("Validating generic format for command [%s]" % command, DEBUG)
        match = self.general_cmd.match(command)
        if match:
            log("Match detected for command [%s]" % command, DEBUG)
            return True
        log("Validating error for command [%s]" % command, DEBUG)
        return False

    def is_valid_helo_command(self, command):
        log("Validating format for helo with command [%s]" % command, DEBUG)
        match = self.helo_cmd.match(command)
        if match:
            log("Command [%s] is a valid helo command" % command, DEBUG)
            return True
        log("Command [%s] is not a valid helo command" % command, DEBUG)
        return False

    def is_valid_read_command(self, command):
        log("Validating format for read with command [%s]" % command, DEBUG)
        match = self.read_cmd.match(command)
        if match:
            log("Command [%s] is a valid read command" % command, DEBUG)
            return True
        log("Command [%s] is not a valid read command" % command, DEBUG)
        return False

    def is_valid_send_command(self, command):
        log("Validating format for send with command [%s]" % command, DEBUG)
        match = self.send_cmd.match(command)
        if match:
            log("Command [%s] is a valid send command" % command, DEBUG)
            return True
        log("Command [%s] is not a valid send command" % command, DEBUG)
        return False

    def is_valid_watch_command(self, command):
        log("Validating format for watch with command [%s]" % command, DEBUG)
        match = self.watch_cmd.match(command)
        if match:
            log("Command [%s] is a valid watch command" % command, DEBUG)
            return True
        log("Command [%s] is not a valid watch command" % command, DEBUG)
        return False

    def is_valid_unwatch_command(self, command):
        log("Validating format for unwatch with command [%s]" % command, DEBUG)
        match = self.unwatch_cmd.match(command)
        if match:
            log("Command [%s] is a valid unwatch command" % command, DEBUG)
            return True
        log("Command [%s] is not a valid unwatch command" % command, DEBUG)
        return False

    def read_g_addr(self, addr):
        match = self.g_addr.match(addr)
        if not match:
            return None

        if len(match.groups()) == 3:
            g1 = int(match.group(1))
            g2 = int(match.group(2))
            g3 = int(match.group(3))
            #r = ((g1 & 0x01F) << 11) | ((g2 & 0x07) << 8) | ((g3 & 0xF))
            r = (g1 << 11) | (g2 << 8) | g3
        else:
            if len(match.groups()) == 2:
                g1 = int(match.group(1))
                g2 = int(match.group(2))
                #r = ((g1 & 0x01F) << 11) | ((g2 & 0x7FF))
                r = (g1 << 11) | g2
            else:
                if len(match.groups()) == 1:
                    g1 = int(match.group(1), 16)
                    #r = (g1 & 0xFFFF)
                    r = g1
                else:
                    raise Exception("Unable to read the given address [%s]" % addr)
        return r

    def read_group_address(self, addr):
        return self.read_g_addr(addr)

    def read_hex(self, val):
        try:
            return int(val, 16)
        except:
            return None

    def _decode_physical_addr(self, raw):
        return "%d.%d.%d" % ((raw >> 12) & 0x0f, (raw >> 8) & 0x0f, (raw) & 0xff)

    def _decode_group_addr(self, raw):
        return "%d/%d/%d" % ((raw >> 11) & 0x1f, (raw >> 8) & 0x07, (raw) & 0xff)

    def read_addr(self, val):
        # read address like %d.%d.%d and transform it to hex value
        parts = val.split('.')
        a = int(parts[0])
        b = int(parts[1])
        c = int(parts[2])
        return ((a & 0x0f) << 12) | ((b & 0x0f) << 8) | ((c & 0xff))

    def read_physical_address(self, val):
        return self.read_addr(val)

    def format_result(self, raw_data):
        result = ''
        if len(raw_data) == 2:
            result += "%02X" % (raw_data[1] & 0x3F)
        else:
            for hex_val in raw_data[2:]:
                result += "%02X " % hex_val
        return result.strip().upper()

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

    print "Test for reading address"
    address = '15/0/1'
    try:
        result = parser.read_g_addr(address)
        print "Result for %s is %d" % (address, result)
        print "OK"
    except Exception, e:
        print "Failed [%s]" % e

    print "Test for reading HEX"
    try:
        result = parser.read_hex('FF')
        assert result == 0xFF
    except Exception, e:
        print "Failed [%s]" %e
    print "OK"

    print "Tests successfully passed"