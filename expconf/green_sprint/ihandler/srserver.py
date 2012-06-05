#!/usr/bin/env python
# 
# This script is a server used to test SR platform.
#
# usage: server.py
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.02.27 created
#

import os
import random
import sys
import time
import struct
import threading
from ctypes import *

sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/')
from common import *
from messageheader import *

class Server(object):
    """This class serves all the requests from the clients."""
    def __init__(self, vrid, ifn, router):
        self.vrid     = vrid
        self.logfh    = None
        self.router   = router
        self.chunks   = load_file(ifn)    # load all the (key,chunk) into a dict
        pass

    def __del__(self):
        pass

    def start_service(self):
        rhdr = MessageHeader()
        buf = ''

        while True:
            try:
                rhdr = self.router.recv()
                if rhdr.type != MessageType.REQUEST:
                    continue

                shdr = MessageHeader()
                shdr.type = MessageType.RESPONSE
                shdr.id = rhdr.id
                shdr.seq = rhdr.seq
                shdr.crid = rhdr.crid
                shdr.control = rhdr.control
                shdr.src = self.vrid
                shdr.dst = rhdr.src
                shdr.hit = 0
                shdr.hop = rhdr.hop + 1
                shdr.data = self.chunks[rhdr.id]

                self.router.send(shdr)
                #print "RESPONSE -> %s" % (str(shdr.dst))
                logme(self.logfh, shdr.seq, shdr.src, shdr.dst, "RSP", shdr.hit, shdr.id, shdr.hop)
            except KeyboardInterrupt:
                break
            except Exception, err:
                print "Exception:Server.start_service():", err
                logme(self.logfh, 0, 0, 0, 'EXCEPT', 0, str(err), 0)

    pass

def main(router, args):
    """Router will call this function"""
    vrid   = args['vrid']
    logdir = args['logdir']
    ifn    = args['app_args']
    server = Server(vrid, ifn, router)
    server.logfh = open("%s/server-%i" % (logdir, vrid), 'w')
    # Liang: debug
    time.sleep(15)
    server.start_service()
    pass


if __name__=="__main__":
    sys.exit(0)
