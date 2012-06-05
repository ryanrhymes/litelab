#!/usr/bin/env python
# 
# This script implements the Neighbour Search caching strategy, with
# Radius, use Cachedbit as admisson policy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.06.02 created
#

import os
import sys
import time
import random
import binascii
import threading
from ctypes import *
from router.common import *
from messageheader import *
from bitarray import bitarray
from pybloom import BloomFilter
from cache_lru import cache_lru

RADIUS = 1

class nbsearch_hop_cachedbit(object):
    def __init__(self, router, cachesize):
        self.router = router
        self.cache = cache_lru(cachesize)
        self.logfh = None
        self.nbbf = {}                   # A dict stores all the neighbours' bloomfiltes
        self.error_rate = 0.01           # The error rate of bloom filter

        t = threading.Thread(target=self.update, args= ())
        t.daemon = True
        t.start()
        pass

    def ihandler(self, hdr, router):
        hdr.hop += 1
        hdr.ttl = hdr.ttl - 1 if hdr.ttl > 0 else 0
        cid = hdr.id
        src = hdr.src
        dst = hdr.dst
        seq = hdr.seq
        drop = False

        if hdr.type == MessageType.REQUEST:
            if self.cache.is_hit(cid):
                # logme2(self.logfh, hdr.seq, src, dst, "REQ", 1, cid)
                hdr.type = MessageType.RESPONSE
                hdr.swap_src_dst()
                hdr.hit = 1
                hdr.data = self.cache.get_chunk(cid)
            else:
                # logme2(self.logfh, hdr.seq, src, dst, "REQ", 0, cid)
                found = self.query_neighbour(hdr)
                if not found and hdr.ttl != 0 and not hdr.is_cached_bit_set():
                    if random.random() <= self.get_save_prob(src, dst):
                        hdr.set_cached_bit()
                        hdr.crid = self.router.id

        elif hdr.type == MessageType.RESPONSE:
            # logme2(self.logfh, hdr.seq, src, dst, "RSP", 0, cid)
            if not self.cache.is_hit(cid):
                if hdr.is_cached_bit_set() and hdr.crid == self.router.id:
                    evict = self.cache.add_chunk(cid, hdr.data)
                    if evict[0]:
                        # logme2(self.logfh, hdr.seq, src, dst, "DEL", 0, evict[0])
                        pass
                    # logme2(self.logfh, hdr.seq, src, dst, "ADD", 0, cid)

        elif hdr.type == MessageType.QUERY:
            hdr.type = MessageType.REQUEST
            hdr.dst = int(hdr.data)
            if self.cache.is_hit(hdr.id):
                # logme2(self.logfh, hdr.seq, src, dst, "QRY", 1, cid)
                hdr.type = MessageType.RESPONSE
                hdr.swap_src_dst()
                hdr.hit = 1
                hdr.data = self.cache.get_chunk(cid)
            else:
                found = self.query_neighbour(hdr)

        elif hdr.type == MessageType.BFBDST:
            self.nbbf[hdr.src] = self.create_bloomfilter_from_string(hdr.data)
            drop = True

        return drop

    def query_neighbour(self, hdr):
        found = False
        if hdr.ttl > 0:
            for nb, bf in self.nbbf.items():
                # There is no need to query the next hop
                if hdr.id in bf and nb != self.router.rtable[hdr.dst]:
                    hdr.type = MessageType.QUERY
                    hdr.data = str(hdr.dst)
                    hdr.dst = nb
                    # Limit the search radius
                    hdr.ttl = RADIUS if hdr.ttl > RADIUS else hdr.ttl
                    found = True
                    break
        return found

    def update(self):
        while True:
            time.sleep(1)
            self.update2neighbour()
        pass

    def update2neighbour(self):
        """This thread update the bloom filter information to the neighbours
        periodically."""
        for nb in self.router.neighbours(self.router.vrid):
            hdr = MessageHeader()
            hdr.type = MessageType.BFBDST
            hdr.src = self.router.vrid
            hdr.dst = nb
            data = self.get_cache_bloomfilter()
            hdr.data = data.bitarray.tostring()
            self.router.send(hdr)
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

    pass


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
