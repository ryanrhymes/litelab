#!/usr/bin/env python
# 
# This script implements the MFR algoritm.
#
# Remark: This algorithm has some inherent problems. Should we consider aging
#         algorithm?
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.06.11 created, 2011.06.13 modified.
#

import os
import sys
import time
import binascii
from ctypes import *
from common import *
from cache_lfu import CacheLFU

class MFR(object):
    def __init__(self, router, cachesize):
        self.router = router
        self.cpt = cache_hdr()
        self.cache = CacheLFU(cachesize)
        self.mfrdict = {}
        self.mfrlist  = []
        self.logfh = None
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
                try:
                    # Update the request frequency
                    xreq = self.mfrdict.get(cid,0) + 1
                    self.mfrdict[cid] = xreq
                    self.mfrlist.remove( (xreq-1,cid) )
                    self.mfrlist.append( (xreq,cid) )
                    self.mfrlist.sort()
                except Exception, err:
                    logme2(self.logfh, self.cpt.seq, ('REQ:'+str(err),0), dst, "EXCEPT", 0, cid)
                    pass

                self.cpt.type = MessageType.RESPONSE
                self.cpt.swap_src_dst()
                self.cpt.hit = 1
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
                        # Add new chunk
                        self.mfrdict[cid] = 1
                        self.mfrlist.append( (1, cid) )
                        self.mfrlist.sort()
                        logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)
                    except Exception, err:
                        print "Exception:MFR.ihandler():", err
                        logme2(self.logfh, self.cpt.seq, ('RSP:1:'+str(err),0), dst, "EXCEPT", 0, cid)
                        pass
                else:
                    try:
                        xreq = 1
                        yreq, ycid = self.mfrlist[-1]
                        if xreq >= yreq:
                            evict = self.cache.add_chunk(cid, self.cpt.data)
                            yreq = self.mfrdict.pop(evict[0])
                            self.mfrlist.remove( (yreq,evict[0]) )
                            # Add new chunk
                            self.mfrdict[cid] = xreq
                            self.mfrlist.append( (xreq,cid) )
                            self.mfrlist.sort()
                            if evict[0]:
                                logme2(self.logfh, self.cpt.seq, src, dst, "DEL", 0, evict[0])
                            logme2(self.logfh, self.cpt.seq, src, dst, "ADD", 0, cid)
                    except Exception, err:
                        print "Exception:MFR.ihandler():", err
                        logme2(self.logfh, self.cpt.seq, ('RSP:2:'+str(err),0), dst, "EXCEPT", 0, str())
                        pass

        return msg


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
