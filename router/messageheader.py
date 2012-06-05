#!/usr/bin/env python
# 
# This file defines the message header used by VRouter
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.12.02 created.
#

import os
import sys
import struct
from ctypes import *

# Some global varialbes
DIGEST_LEN  = 20

class MessageType():
    REQUEST  = 0
    RESPONSE = 1
    ALIVE    = 2
    PUSH     = 3
    DIGEST   = 4
    BFBDST   = 5
    QUERY    = 6
    ANSWER   = 7
    pass

class MessageHeader(Structure):
    """This class defines the message header."""

    _fields_ = [ ("type",     c_uint),
                 ("_id",      c_ubyte * DIGEST_LEN),
                 ("seq",      c_uint),
                 ("control",  c_ubyte),
                 # ("neighbor", c_ubyte),
                 # ("_visited", c_ubyte * DIGEST_LEN),
                 ("_crid",    c_ubyte * DIGEST_LEN),
                 ("src",      c_int32),
                 ("dst",      c_int32),
                 ("nxt",      c_int32),   # next hop, -1 means unset
                 ("ttl",      c_ushort),
                 ("hit",      c_ushort),  # test purpose
                 ("hop",      c_ushort) ]

    def __init__(self):
        self.nxt = -1
        self.ttl = 64
        self.data = ''
        pass

    def send(self):
        """Convert struct to stream."""
        return buffer(self)[:] + self.data

    def recv(self, bytes):
        """Convert stream to struct."""
        head_len = sizeof(self)
        memmove(addressof(self), bytes, head_len)
        self.data = bytes[head_len:]
        pass

    @property
    def id(self):
        return self.get_char_array(self._id)

    @id.setter
    def id(self, val):
        self.set_char_array(self._id, val)

    @property
    def visited(self):
        return self.get_char_array(self._visited)

    @visited.setter
    def visited(self, val):
        self.set_char_array(self._visited, val)

    @property
    def crid(self):
        return self.get_char_array(self._crid)

    @crid.setter
    def crid(self, val):
        self.set_char_array(self._crid, val)

    def set_char_array(self, dest, src, length=DIGEST_LEN):
        memmove(addressof(dest), src, length)
        pass

    def get_char_array(self, src, length=DIGEST_LEN):
        p = cast(addressof(src), POINTER(c_char * length))
        return p.contents.raw

    def set_cached_bit(self):
        self.control |= 0x10
        pass

    def unset_cached_bit(self):
        self.control &= 0xEF
        pass

    def is_cached_bit_set(self):
        return self.control & 0x10

    def swap_src_dst(self):
        tvar = self.src
        self.src = self.dst
        self.dst = tvar
        pass

    pass
