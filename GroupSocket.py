__author__ = 'mehdi'

import Dpt_Types
import time


class groupsocket:
    def __init__(self, parent):
        self._parent = parent
        if parent:
            self.WG = parent.WG
        else:
            self.WG = False
        self.nicehex = lambda x: " ".join(map(lambda y: "%.2x" % y, x))
        self.tobinstr = lambda n, b=8: "".join([str((n >> y) & 1) for y in range(b - 1, -1, -1)])
        self.dpt = Dpt_Types.dpt_type(self)

    def decode(self, buf, src, dst):
        ## Accept List Hex or Binary Data
        if type(buf) == str:
            tmp = buf
            buf = []
            try:
                ##Hex or Binary
                if ord(tmp[0]) > 122:
                    ##Binary
                    for char in tmp:
                        buf.append(ord(char))
                else:
                    ##Hex
                    for hex in range(0, len(tmp), 2):
                        buf.append(int(tmp[hex:hex + 2], 16))
            except:
                self.errormsg(tmp)

        msg = {'raw': buf, 'src': src, 'dst': dst, 'srcaddr': self._decodePhysicalAddr(src)}
        try:
            msg['dstaddr'] = self._decodeGrpAddr(dst)
            id = "%s:%s" % (self._parent.instanceName, msg['dstaddr'])
            if buf[0] & 0x3 or (buf[1] & 0xC0) == 0xC0:
                ##FIXME: unknown APDU
                self.debug("unknown APDU from %r to %r raw: %r" % (msg['srcaddr'], msg['dstaddr'], buf))
            else:
                dsobj = self.WG.DATASTORE.get(id)
                if buf[1] & 0xC0 == 0x00:
                    msg['type'] = "read"
                    if dsobj.config.get('readflag', False):
                        self.debug("Read from %s" % id)
                        self._parent.setValue(dsobj, flag=0x40)

                #FIXME: Check (ds) if we should respond
                elif (buf[1] & 0xC0 == 0x40) or (buf[1] & 0xC0 == 0x80):
                    if buf[1] & 0xC0 == 0x40:
                        msg['type'] = "response"
                    else:
                        msg['type'] = "write"
                        ## search Datastoreobject

                    ## Decode the DPT Value
                    if len(buf) > 2:
                        msg['value'] = self.dpt.decode(buf[2:], dsobj=dsobj)
                    else:
                        msg['value'] = self.dpt.decode([buf[1] & 0x3F], dsobj=dsobj)
                        ## update Object in Datastore
                        self.WG.DATASTORE.update(id,msg['value'])
        except:
            self.errormsg(msg)

        #self.debug(msg)
        return msg

    def errormsg(self, msg=False):
        ## central error handling
        self.WG.errorlog(msg)

    def _decodePhysicalAddr(self, raw):
        return "%d.%d.%d" % ((raw >> 12) & 0x0f, (raw >> 8) & 0x0f, (raw) & 0xff)

    def _decodeGrpAddr(self, raw):
        return "%d/%d/%d" % ((raw >> 11) & 0x1f, (raw >> 8) & 0x07, (raw) & 0xff)

    def log(self, msg, severity='info', instance=False):
        if not instance:
            instance = 'KNX'
        self._parent.log(msg, severity, instance)

    def debug(self, msg):
        self.log("DEBUG: GROUPSOCKET: " + repr(msg), 'debug')
        pass


if __name__ == "__main__":
    groupsocket = groupsocket(False)
    #print "DEBUG " + groupsocket.decode([1,128, 110, 111])