#!/usr/bin/env python
# 
# This script implements SmartRE Shim header.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.12.06 created
#

import os
import sys
from ctypes import *

class SmartREShim(Structure):
    """Implement SmartRE Shim header according to Anand's paper."""

    _pack_ = 1

    _fields_ = [ ("_pathid",   c_int32),
                 ("_matches",  c_uint16) ]

    def __init__(self):
        self.matches = 0
        self.matchspecs = []
        self.data = ''
        pass

    def send(self):
        s = buffer(self)[:]
        for m in self.matchspecs:
            s += m.send()
        s += self.data
        return s

    def recv(self, bytes):
        mlen = sizeof(self)
        fit = min(mlen, len(bytes))
        memmove(addressof(self), bytes, fit)
        for i in range(self.matches):
            m = MatchSpec()
            m.recv(bytes[mlen + i * sizeof(MatchSpec) : mlen + (i + 1) * sizeof(MatchSpec)])
            self.matchspecs.append(m)
        self.data = bytes[mlen + self.matches * sizeof(MatchSpec) : ]
        pass

    @property
    def pathid(self):
        return self._pathid

    @pathid.setter
    def pathid(self, val):
        self._pathid = c_int32(val)

    @property
    def matches(self):
        return self._matches

    @matches.setter
    def matches(self, val):
        self._matches = c_uint16(val)

    def add_matchspec(self, pathid, header_hash, region, position):
        match = MatchSpec(pathid, header_hash, region, position)
        self.matchspecs.append(match)
        self.matches += 1
        pass

    def del_matchspec(self, m):
        """Delete a matchspec, and adjust the postion in other matchspecs"""
        index = self.matchspecs.index(m)
        self.matchspecs.pop(index)
        self.matches -= 1
        shift = m.region[1] - m.region[0]
        for x in self.matchspecs:
            if x.position > m.position:
                x.position += shift
        pass

    pass


class MatchSpec(Structure):
    """Used in SmartREShim, and contains detail information of a match."""

    _pack_ = 1

    _fields_ = [ ("_pathid", c_int32),        # PathId of matched packet
                 ("_header_hash", c_float),   # Hash of matched packet header
                 ("_region_start", c_uint16), # Matched region in cached packet
                 ("_region_stop", c_uint16),  # Matched region in cached packet
                 ("_position", c_uint16) ]    # Position of shim in THIS packet

    def __init__(self, pathid=None, header_hash=None, 
                 region=None, position=None):
        if pathid is not None:
            self.pathid = pathid
        if header_hash is not None:
            self.header_hash = header_hash
        if region is not None:
            self.region = region
        if position is not None:
            self.position = position
        pass

    def send(self):
        return buffer(self)[:]

    def recv(self, bytes):
        mlen = sizeof(self)
        fit = min(mlen, len(bytes))
        memmove(addressof(self), bytes, fit)
        pass

    @property
    def pathid(self):
        return self._pathid

    @pathid.setter
    def pathid(self, val):
        self._pathid = c_int32(val)

    @property
    def header_hash(self):
        return self._header_hash

    @header_hash.setter
    def header_hash(self, val):
        self._header_hash = c_float(val)

    @property
    def region(self):
        return (self._region_start, self._region_stop)

    @region.setter
    def region(self, val):
        rstart, rstop = val
        self._region_start = c_uint16(rstart)
        self._region_stop = c_uint16(rstop)

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, val):
        self._position = c_uint16(val)

    pass
