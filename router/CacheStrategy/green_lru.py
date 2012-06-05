#!/usr/bin/env python
# 
# This script implements the LRU algorithm for Green INCA.
# Python list is used, insert the new entry to head, and pop the old one from
# the tail.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.29 created
#

import os
import sys
import time
import binascii
from ctypes import *
from router.common import *
from messageheader import *
from cache_lru import cache_lru


class green_lru(object):
    def __init__(self, router, cachesize):
        self.router = router
        self.cache = cache_lru(cachesize)
        self.logfh = None
        pass

    def ihandler(self, hdr, router):
        hdr.hop += 1
        cid = hdr.id
        src = hdr.src
        dst = hdr.dst

        if hdr.hop > 64:
            return True

        if hdr.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                logme2(self.logfh, hdr.seq, src, dst, "REQ", 1, cid)
                hdr.type = MessageType.RESPONSE
                hdr.swap_src_dst()
                hdr.hit = 1
                hdr.data = self.cache.get_chunk(cid)
            else:
                logme2(self.logfh, hdr.seq, src, dst, "REQ", 0, cid)

        elif hdr.type == MessageType.RESPONSE:
            logme2(self.logfh, hdr.seq, src, dst, "RSP", 0, cid)
            if not self.cache.is_hit(cid):
                evict = self.cache.add_chunk(cid, hdr.data)
                if evict[0]:
                    logme2(self.logfh, hdr.seq, src, dst, "DEL", 0, evict[0])
                logme2(self.logfh, hdr.seq, src, dst, "ADD", 0, cid)

        return False


if __name__ == "__main__":
    print sys.argv[0]
    sys.exit(0)
