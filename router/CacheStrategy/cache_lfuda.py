#!/usr/bin/env python
# 
# This script implements the cache model with LFU replacement algorithm with
# dynamic aging.
#
# Formula: Pr(f) = L + Fr(f)
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.07.11 created
#

import os
import sys
import time
import bisect
import binascii
from ctypes import *
from common import *
from operator import itemgetter, attrgetter

class cache_lfuda(object):
    def __init__(self, quota):
        self.cache = {}
        self.llist = []
        self.clock = 0
        self.quota = quota
        self.pathcache ={}
        self.logfh = None
        pass

    @property
    def keys(self):
        return self.cache.keys()

    def add_chunk(self, key, val):
        evict = (None, None)
        if not self.cache.has_key(key) and self.quota > 0:
            if len(self.llist) >= self.quota:
                # well, run of space now
                _, _, oldkey = self.llist[0]
                evict = self.del_chunk(oldkey)
            self.cache[key] = val
            bisect.insort_right(self.llist, [1+self.clock,time.time(),key])
        return evict

    def get_chunk(self, key):
        val = self.cache.get(key, None)
        if val:
            y = None
            for x in self.llist:
                if x[2] == key:
                    y = list(x)
                    self.llist.remove(x)
                    break
            if y:
                y[0] += self.clock + 1
                y[1] = time.time()
                bisect.insort_right(self.llist, y)
        return val

    def del_chunk(self, key):
        evict = (None, None)
        if self.cache.has_key(key):
            evict = (key,self.cache.pop(key))
            for x in self.llist:
                if x[2] == key:
                    self.clock = x[0]
                    self.llist.remove(x)
                    break
        return evict

    def add_pathcache(self, key, src, dst):
        self.pathcache[key] = (src,dst)
        pass

    def del_pathcache(self, key):
        src, dst = self.pathcache.pop(key)
        return src,dst

    def current_size(self):
        return len(self.cache)

    def is_full(self):
        return len(self.llist) >= self.quota

    def is_hit(self, key):
        return self.cache.has_key(key)

    def get_val_by_key(self, key):
        """Remark: Pay attention to the differences between this function and
        get_chunk(...) function."""
        val = self.cache.get(key, None)
        return val

    pass


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
