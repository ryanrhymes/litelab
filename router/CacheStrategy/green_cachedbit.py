#!/usr/bin/env python
# 
# This script implements the Green CachedBit caching strategy, which
# is modified based on CachedBit. The difference is how to calcuate
# caching probability.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.03.26 created
#

import os
import sys
import time
import binascii
from ctypes import *
from router.common import *
from messageheader import *
from cache_lru import cache_lru


class green_cachedbit(object):
    def __init__(self, router, cachesize):
        self.router = router             # Cache's corresponding router
        self.cache = cache_lru(cachesize)
        self.hopch = {}  # cache for hop count
        self.logfh = None
        pass

    def ihandler(self, hdr, router):
        hdr.hop += 1
        cid = hdr.id
        src = hdr.src
        dst = hdr.dst

        if hdr.hop > 64:
            return True

        self.update_hopch(hdr)

        if hdr.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                logme2(self.logfh, hdr.seq, src, dst, "REQ", 1, cid)
                hdr.type = MessageType.RESPONSE
                hdr.swap_src_dst()
                hdr.hit = 1
                hdr.data = self.cache.get_chunk(cid)
            else:
                logme2(self.logfh, hdr.seq, src, dst, "REQ", 0, cid)
                if not hdr.is_cached_bit_set():
                    if random.random() <= self.get_save_prob(src, dst):
                        hdr.set_cached_bit()
                        hdr.crid = self.router.id

        elif hdr.type == MessageType.RESPONSE:
            logme2(self.logfh, hdr.seq, src, dst, "RSP", 0, cid)
            if not self.cache.is_hit(cid):
                if hdr.is_cached_bit_set() and hdr.crid == self.router.id:
                    evict = self.cache.add_chunk(cid, hdr.data)
                    if evict[0]:
                        logme2(self.logfh, hdr.seq, src, dst, "DEL", 0, evict[0])
                    logme2(self.logfh, hdr.seq, src, dst, "ADD", 0, cid)

        return False

    def get_save_prob(self, src, dst):
        p = 1.0
        s2d = self.hopch.get((src, dst), -1)
        d2s = self.hopch.get((dst, src), -1)

        if d2s <= 0:
            p = 1.0 / s2d
        else:
            p = 1.0 / ((s2d + d2s) / 2.0 - 1)

        return p

    def update_hopch(self, hdr):
        src = hdr.src
        dst = hdr.dst
        hop = hdr.hop - 1
        s2d = self.hopch.get((src, dst), -1)
        if hop != s2d and hdr.hit != 1:
            self.hopch[(src, dst)] = hop
        pass

    def get_save_prob_orig(self, src, dst):
        p = 1.0
        dist = (len(self.router.pathdict[(src, self.router.vrid)])
                + len(self.router.pathdict[(self.router.vrid, dst)]) - 3)
        dist = dist if dist > 0 else 1
        p = p / dist
        return p


if __name__ == "__main__":
    print sys.argv[0]
    sys.exit(0)
