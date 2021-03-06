#!/usr/bin/env python
# 
# This script is modified based on pushcache.py. Beside the basic
# functionalities provided in pushcache.py, it also adopts probability caching
# in the caching strategy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.07.25 created
#

import os
import sys
import random
import binascii
from ctypes import *
from common import *
from cache_lru import CacheLRU

class PushProb(object):
    def __init__(self, router, cachesize):
        self.router = router             # Cache's corresponding router
        self.cpt = cache_hdr()
        self.cache = CacheLRU(cachesize)
        self.logfh = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pass

    def ihandler(self, msg):
        self.cpt.recv(msg)
        self.cpt.hop += 1
        msg = self.cpt.send() + self.cpt.data
        cid = self.cpt.id
        src = self.cpt.src
        dst = self.cpt.dst

        if self.cpt.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                print "HIT"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 1, cid)
                self.cpt.type = MessageType.RESPONSE
                self.cpt.swap_src_dst()
                self.cpt.hit = 1

                msg = self.cpt.send() + self.cache.get_chunk(cid)
            else:
                print "MISS"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 0, cid)
                if self.router.is_edge(src, dst):
                    self.cpt.set_cached_bit()
                    self.cpt.crid = self.router.id
                    msg = self.cpt.send() + self.cpt.data

        elif self.cpt.type == MessageType.RESPONSE:
            logme2(self.logfh, self.cpt.seq, src, dst, "RSP", 0, cid)
            
            if ( self.cpt.is_cached_bit_set() and self.cpt.crid == self.router.id ) or \
                    ( random.random() <= self.get_save_prob(src, dst) ):
                print "Caching data", self.cache.current_size()
                # Flip the src and dst because it is a RESPONSE
                self.cache.add_pathcache(cid, dst, src)
                evict = self.cache.add_chunk(cid, self.cpt.data)
                if evict[0]:
                    osrc, odst = self.cache.del_pathcache(evict[0])
                    print osrc, odst, '+'*100
                    self.push2up(evict[0], evict[1], osrc, odst)
                    logme2(self.logfh, self.cpt.seq, src, dst, "DEL", 0, evict[0])
                logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)

        elif self.cpt.type == MessageType.PUSH:
            print "Receive PUSH message", self.cache.current_size()
            self.cache.add_pathcache(cid, src, dst)
            evict = self.cache.add_chunk(cid, self.cpt.data)
            if evict[0]:
                print '='*100
                osrc, odst = self.cache.del_pathcache(evict[0])
                self.push2up(evict[0], evict[1], osrc, odst)
            msg = None

        return msg

    def push2up(self, cid, chunk, src, dst):
        path = self.router.pathdict[(src,dst)]
        pos  = path.index( (self.router.ilink) )
        upr  = path[pos+1]
        if upr != dst:
            scpt = cache_hdr()
            scpt.type = MessageType.PUSH
            scpt.id = cid
            scpt.src = src
            scpt.dst = dst
            msg = scpt.send() + chunk
            self.sock.sendto(msg, self.router.elink)
        pass

    def get_save_prob(self, src, dst):
        p = 1.0
        dist = len(self.router.pathdict[(src,dst)]) - 2
        dist = dist if dist > 0 else 1
        p = p / dist
        return p


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
