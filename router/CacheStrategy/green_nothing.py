#!/usr/bin/env python
# 
# This script implements "nothing", :)
# When use this as caching strategy, SRouter simply becomes a
# forwarder. Only the traffic log is maintained.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.04.11 created
#

import os
import sys
import time
import binascii
from ctypes import *
from router.common import *
from messageheader import *


class green_nothing(object):
    def __init__(self, router, cachesize):
        self.router = router
        self.cache = None
        self.logfh = None
        self.mdict = {
            MessageType.REQUEST: 'REQ',
            MessageType.RESPONSE: 'RSP',
            MessageType.ALIVE: 'LIV',
            MessageType.PUSH: 'PSH',
            MessageType.DIGEST: 'DGT',
            MessageType.BFBDST: 'BFB',
            MessageType.REQUEST: 'REQ',
            MessageType.QUERY: 'QRY',
            MessageType.ANSWER: 'ANS',
            }
        pass

    def ihandler(self, hdr, router):
        hdr.hop += 1
        cid = hdr.id
        src = hdr.src
        dst = hdr.dst

        if hdr.hop > 64:
            return True

        logme2(self.logfh, hdr.seq, src, dst, self.mdict[hdr.type], 0, cid)
        return False


if __name__ == "__main__":
    print sys.argv[0]
    sys.exit(0)
