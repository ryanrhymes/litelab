#!/usr/bin/env python
# 
# This script implements the abstraction of cache object in a router. The
# replacement algorithem is FIFO. And the cache block are organized into
# buckets. The cache model is used in SmartRE experiment.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.12.06 created
#

import os
import sys


class cache_fifobucket(object):
    """Cache model uses FIFO as replacement algorithm. Blocks are
    organized into buckets."""

    def __init__(self, quota):
        self.quota = quota
        self.bucket = {}
        self.bucket_index = {}
        self.bucket_quota = {}
        self.hh2ix = {}    # From header_hash to index
        self.ix2hh = {}    # From index to header_hash
        self.fp2ix = {}    # From fingerprint to index
        self.ix2fp = {}    # From index to fingerprints
        pass

    def init_bucket(self, bucket_quota):
        for pathid, vrid, quota in bucket_quota:
            self.bucket[pathid] = self.bucket.get(pathid, dict())
            self.bucket_index[pathid] = self.bucket_index.get(pathid, dict())
            self.bucket_quota[pathid] = self.bucket_quota.get(pathid, dict())

            self.bucket[pathid][vrid] = [None] * quota
            self.bucket_index[pathid][vrid] = 0
            self.bucket_quota[pathid][vrid] = quota
        pass

    def add_chunk(self, pathid, vrid, header_hash, chunk, fps=None):
        bindex = self.bucket_index[pathid][vrid]
        # Delete fingerprints and header_hash if a chunk is evicted
        self.del_chunk(pathid, vrid, bindex)

        self.bucket[pathid][vrid][bindex] = chunk
        self.hh2ix[header_hash] = (pathid, vrid, bindex)
        self.ix2hh[(pathid, vrid, bindex)] = header_hash
        if fps is not None:
            self.add_fingerprints(pathid, vrid, bindex, fps)

        bindex = (bindex + 1) % self.bucket_quota[pathid][vrid]
        self.bucket_index[pathid][vrid] = bindex
        pass

    def get_chunk(self, pathid, vrid, index):
        chunk = self.bucket[pathid][vrid][index]
        return chunk

    def del_chunk(self, pathid, vrid, index):
        header_hash = self.ix2hh.get((pathid, vrid, index), None)
        if header_hash is not None:
            self.ix2hh.pop((pathid, vrid, index))
            self.hh2ix.pop(header_hash)

        fps = self.ix2fp.get((pathid, vrid, index), None)
        if fps is not None:
            self.ix2fp.pop((pathid, vrid, index))
            for fp, _ in fps:
                self.fp2ix[fp].pop(pathid)
                if len(self.fp2ix[fp]) == 0:
                    self.fp2ix.pop(fp)
        pass

    def add_fingerprints(self, pathid, vrid, index, fps):
        for fp, offset in fps:
            if not self.fp2ix.has_key(fp):
                self.fp2ix[fp] = {}
            self.fp2ix[fp][pathid] = (pathid, vrid, index, offset)
        self.ix2fp[(pathid, vrid, index)] = fps
        pass

    def get_index_by_fp(self, fp):
        """Given the fingerprint, return the index info of the chunk"""
        info = self.fp2ix.get(fp, None)
        #obj = self.fp2ix.get(fp, None)
        #if obj is not None:
        #    for pathid in candidates:
        #        info = obj.get(pathid, None)
        #        if info is not None:
        #            break
        return info

    def get_index_by_hh(self, header_hash):
        """Given the header hash, return the index info of the chunk"""
        info = self.hh2ix.get(header_hash, None)
        return info

    def get_hh_by_index(self, pathid, vrid, index):
        """Given the index infomation, return the header hash"""
        hh = self.ix2hh.get((pathid, vrid, index), None)
        return hh

    def is_full(self):
        return False

    pass
