#!/usr/bin/env python
# 
# This script implements the Probability CachedBit caching strategy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.31 created
#

import os
import sys
import time
import binascii
from ctypes import *
from router.common import *
from messageheader import *
from cachedbit import cachedbit


class pcachedbit(cachedbit):
    def __init__(self, router, cachesize):
        super(pcachedbit, self).__init__(router, cachesize)
        self.probc = {}       # Cache for the probability already been calculated
        pass

    def ihandler(self, hdr, router):
        return super(pcachedbit, self).ihandler(hdr, router)

    def get_save_prob(self, src, dst):
        p = 1.0
        if self.probc.has_key( (src,dst) ):
            p = self.probc[ (src,dst) ]
        else:
            dist = len(self.router.pathdict[(src,dst)]) - 2
            dist = dist if dist > 0 else 1
            t = 0.0
            for x in range(1, dist+1):
                t += self.prob_distr(x)
            pos = 1
            try:
                pos = self.router.pathdict[(src,dst)].index(self.router.vrid)
            except Exception, err:
                logme2(self.logfh, 0, src, dst, "EXCEPT_PATH", 0, '')
            p = self.prob_distr(pos) / t
        return p

    def prob_distr(self, x):
        """Currently, use 1/x as default distribution."""
        return 1.0/x


if __name__ == "__main__":
    print sys.argv[0]
    sys.exit(0)
