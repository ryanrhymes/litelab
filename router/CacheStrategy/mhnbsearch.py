#!/usr/bin/env python
# 
# This script implements the Multi-Hop Neighbour Search caching strategy.
# The caching strategy is based on CachedBit strategy. Others can also be
# considered.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.06.10 created
#

import os
import sys
import time
import random
import binascii
import threading
from ctypes import *
from common import *
from bitarray import bitarray
from pybloom import BloomFilter
from cache_lru import CacheLRU

MAXHOPS = 2    # Define the radius of neighbour search.

class MHNbSearch(object):
    def __init__(self, router, cachesize):
        self.router = router             # Cache's corresponding router
        self.cpt = cache_hdr()
        self.cache = CacheLRU(cachesize)
        self.logfh = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nbbf = {}                   # A dict stores all the neighbours' bloomfiltes
        self.error_rate = 0.01           # The error rate of bloom filter
        self.holdback = {}               # A dict holdback the messages

        t = threading.Thread(target=self.update, args= ())
        t.daemon = True
        t.start()
        pass

    def ihandler(self, msg):
        self.cpt.recv(msg)
        cid = self.cpt.id
        src = self.cpt.src
        dst = self.cpt.dst
        seq = self.cpt.seq

        if self.cpt.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                print "HIT"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 1, cid)
                self.cpt.type = MessageType.RESPONSE
                self.cpt.swap_src_dst()
                # If this chunk has been cached, then no need to cache it
                # again in downstream.
                if self.cpt.is_cached_bit_set():
                    self.cpt.unset_cached_bit()
                    self.cpt.crid = self.router.id
                msg = self.cpt.send() + self.cache.get_chunk(cid)
            else:
                print "MISS"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 0, cid)
                tcpt = cache_hdr()
                tcpt.recv(msg)
                tcpt.ttl = MAXHOPS
                for nb in self.router.neighbours(self.router.ilink):
                    # There is no need to query the prev hop. However, it NOT
                    # implemented yet. I will do it later!
                    self.holdback[(cid,seq)] = tcpt
                    self.query_neighbour(tcpt, nb)
                msg = None

                """if msg and not self.cpt.is_cached_bit_set():
                    if random.random() <= self.get_save_prob(src, dst):
                        self.cpt.set_cached_bit()
                        self.cpt.crid = self.router.id
                        msg = self.cpt.send() + self.cpt.data
                """

        elif self.cpt.type == MessageType.RESPONSE:
            logme2(self.logfh, self.cpt.seq, src, dst, "RSP", 0, cid)
            if not self.cache.is_hit(cid):
                if self.cpt.is_cached_bit_set() and self.cpt.crid == self.router.id:
                    print "Caching data", self.cache.current_size()
                    evict = self.cache.add_chunk(cid, self.cpt.data)
                    if evict[0]:
                        logme2(self.logfh, self.cpt.seq, src, dst, "DEL", 0, evict[0])
                    logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)

        return msg

    def chandler(self, msg):
        rcpt = cache_hdr()
        rcpt.recv(msg)

        if rcpt.type == MessageType.QUERY:
            msg = rcpt.send()
            if self.cache.is_hit(rcpt.id):
                rcpt.type = MessageType.ANSWER
                rcpt.dst = rcpt.src
                rcpt.src = self.router.ilink
                # Liang: Should we delete the cache here on this router?
                msg += self.cache.get_chunk(rcpt.id)
                self.sock.sendto(msg, self.router.elink)
            else:
                rcpt.ttl -= 1
            msg = None
        elif rcpt.type == MessageType.ANSWER:
            # The first response decides the whole behaviour
            if self.holdback.has_key( (rcpt.id,rcpt.seq) ):
                scpt = self.holdback.pop( (rcpt.id,rcpt.seq) )
                if len(rcpt.data):
                    scpt.type = MessageType.RESPONSE
                    scpt.swap_src_dst()
                msg = scpt.send() + rcpt.data
                self.sock.sendto(msg, self.router.elink)
            msg = None
        return msg

    def query_neighbour(self, cpt, addr):
        scpt = cache_hdr()
        scpt.id = cpt.id
        scpt.seq = cpt.seq
        scpt.ttl = cpt.ttl
        scpt.type = MessageType.QUERY
        scpt.src = self.router.ilink
        scpt.dst = addr
        msg = scpt.send()
        self.sock.sendto(msg, self.router.elink)
        pass

    def update(self):
        while True:
            time.sleep(1)
            self.update2neighbour()
            print "update neighbours, holdback =", len(self.holdback)
        pass

    def update2neighbour(self):
        """This thread update the bloom filter information to the neighbours
        periodically."""
        scpt = cache_hdr()
        scpt.type = MessageType.BFBDST
        scpt.src = self.router.ilink
        data = self.get_cache_bloomfilter()
        data = data.bitarray.tostring()

        for nb in self.router.neighbours(self.router.ilink):
            scpt.dst = nb
            msg = scpt.send() + data
            self.sock.sendto(msg, self.router.elink)
        pass

    def get_cache_bloomfilter(self):
        bf = self.create_empty_bloomfilter()
        for cid in self.cache.keys:
            bf.add(cid)
        return bf

    def create_empty_bloomfilter(self):
        """Create an empty bloom filter with byte aligness."""
        bf = BloomFilter(capacity=self.cache.quota, error_rate=self.error_rate)
        bs = bf.bitarray.tostring()
        bf.bitarray = bitarray()
        bf.bitarray.fromstring(bs)
        return bf

    def create_bloomfilter_from_string(self, s):
        bf = self.create_empty_bloomfilter()
        bf.bitarray = bitarray()
        bf.bitarray.fromstring(s)
        return bf

    def get_save_prob(self, src, dst):
        p = 1.0
        dist = len(self.router.pathdict[(src,dst)]) - 2
        dist = dist if dist > 0 else 1
        p = p / dist
        return p


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
