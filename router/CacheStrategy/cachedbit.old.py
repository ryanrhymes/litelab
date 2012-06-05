#!/usr/bin/env python
# 
# This script implements the CachedBit caching strategy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.31 created
#

import os
import sys
import binascii
from ctypes import *
from common import *
from cache import Cache

class CachedBit(object):
    def __init__(self, crid):
        self.crid = crid            # Cache's corresponding router's id.
        self.cpt = cache_hdr()
        self.cache = Cache(5000)
        self.logfh = None
        pass

    def ihandler(self, msg):
        self.cpt.recv(msg)
        cid = self.cpt.get_char_array(self.cpt.id)
        src = self.cpt.get_src_addr()
        dest = self.cpt.get_dest_addr()

        if self.cpt.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                print "HIT"
                logme(self.logfh, "%s:%i\t%s:%i\t%s\t%i\t%s" % (src[0],src[1],dest[0],dest[1],"REQ", 1, binascii.hexlify(cid)))
                self.type = MessageType.RESPONSE
                self.cpt.swap_src_dest()
                msg = self.cpt.send() + self.cache.get_val_by_key(cid)
            else:
                print "MISS"
                if not self.cpt.is_cached_bit_set():
                    self.cpt.set_cached_bit()
                    self.cpt.set_char_array(self.cpt.cr_id, self.crid)
                    msg = self.cpt.send() + self.cpt.data
                logme(self.logfh, "%s:%i\t%s:%i\t%s\t%i\t%s" % (src[0],src[1],dest[0],dest[1],"REQ", 0, binascii.hexlify(cid)))
        elif self.cpt.type == MessageType.RESPONSE:
            if not self.cache.is_hit(cid):
                if self.cpt.is_cached_bit_set() and self.cpt.get_char_array(self.cpt.cr_id) == self.crid:
                    print "Caching data", self.cache.current_size(), self.cpt.is_cached_bit_set()
                    evict = self.cache.add_chunk(cid, self.cpt.data)
                    logme(self.logfh, "%s:%i\t%s:%i\t%s\t%i\t%s" % (src[0],src[1],dest[0],dest[1],"RSP", 0, binascii.hexlify(cid)))
                    if evict:
                        logme(self.logfh, "%s:%i\t%s:%i\t%s\t%i\t%s" % (src[0],src[1],dest[0],dest[1],"DEL", 0, binascii.hexlify(evict)))
                        logme(self.logfh, "%s:%i\t%s:%i\t%s\t%i\t%s" % (src[0],src[1],dest[0],dest[1],"ADD", 0, binascii.hexlify(cid)))
        return msg


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
