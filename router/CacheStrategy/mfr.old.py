#!/usr/bin/env python
# 
# This script implements the MFR algoritm. Currently, we use the simple method
# which maintains all the requests for a chunk that the router has seen.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.06.11 created.
#

import os
import sys
import time
import binascii
from ctypes import *
from common import *
from cache_lru import CacheLRU

class MFR(object):
    def __init__(self, router, cachesize):
        self.router = router
        self.cpt = cache_hdr()
        self.cache = CacheLRU(cachesize)
        self.mfrdict = {}
        self.mfrlist  = []
        self.logfh = None
        pass

    def ihandler(self, msg):
        self.cpt.recv(msg)
        cid = self.cpt.id
        src = self.cpt.src
        dst = self.cpt.dst
        if self.cpt.type == MessageType.REQUEST:
            # Update the request frequency
            xreq = self.mfrdict.get(cid,0) + 1
            self.mfrdict[cid] = xreq
            try:
                if (xreq-1,cid) in self.mfrlist:
                    self.mfrlist.remove( (xreq-1,cid) )
                    self.mfrlist.append( (xreq,cid) )
                    self.mfrlist.sort()
            except Exception, err:
                logme2(self.logfh, self.cpt.seq, src, dst, "EXCEPT", 0, err)
                pass

            if self.cache.is_hit(cid):
                print "HIT"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 1, cid)
                self.cpt.type = MessageType.RESPONSE
                self.cpt.swap_src_dst()
                msg = self.cpt.send() + self.cache.get_chunk(cid)
            else:
                print "MISS"
                logme2(self.logfh, self.cpt.seq, src, dst, "REQ", 0, cid)

        elif self.cpt.type == MessageType.RESPONSE:
            logme2(self.logfh, self.cpt.seq, src, dst, "RSP", 0, cid)
            if not self.cache.is_hit(cid):
                if not self.cache.is_full():
                    try:
                        self.cache.add_chunk(cid, self.cpt.data)
                        self.mfrlist.append( (self.mfrdict[cid], cid) )
                        self.mfrlist.sort()
                        logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)
                    except Exception, err:
                        print "Exception:MFR.ihandler():", err
                        logme2(self.logfh, self.cpt.seq, src, dst, "EXCEPT", 0, err)
                        pass
                else:
                    try:
                        xreq = self.mfrdict[cid]
                        yreq, ycid = self.mfrlist[-1]
                        if xreq > yreq:
                            self.cache.del_chunk(ycid)
                            logme2(self.logfh, self.cpt.seq, src, dst, "DEL", 0, ycid)
                            self.cache.add_chunk(cid, self.cpt.data)
                            self.mfrlist[-1] = (xreq,cid)
                            self.mfrlist.sort()
                            logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)
                    except Exception, err:
                        print "Exception:MFR.ihandler():", err
                        logme2(self.logfh, self.cpt.seq, src, dst, "EXCEPT", 0, err)
                        pass

        return msg


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
