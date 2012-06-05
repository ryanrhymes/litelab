#!/usr/bin/env python
# 
# This script implements the abstraction of cache object in a router. The
# relevant operations on cache can be implemented in this class.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.31 created, 2011.06.12 modified.
#

import os
import sys
import binascii
from ctypes import *
from common import *

class Cache(object):
    def __init__(self, quota):
        self.cache = {}
        self.llist = []
        self.quota = quota
        self.pathcache ={}
        self.logfh = None
        pass

    @property
    def keys(self):
        return self.llist

    def add_chunk(self, key, val):
        evict = (None, None)
        if not self.cache.has_key(key):
            if len(self.llist) < self.quota:
                # we still have spare space
                self.cache[key] = val
            else:
                # well, run of space now
                evkey = self.llist.pop()
                edata = self.cache.pop(evkey)
                evict = (evkey,edata)
                self.cache[key] = val
            self.llist.insert(0, key)
        return evict

    def get_chunk(self, key):
        val = self.cache.get(key, None)
        if val:
            self.llist.remove(key)
            self.llist.insert(0, key)
        return val

    def del_chunk(self, key):
        evict = (None, None)
        if self.cache.has_key(key):
            self.llist.remove(key)
            evict = (key,self.cache.pop(key))
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
