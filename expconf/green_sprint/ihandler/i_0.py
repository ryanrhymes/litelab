#!/usr/bin/env python

import os
import sys
import time

def ihandler(hdr, router):
    nexthop = router.rtable.get((hdr.src, hdr.dst), None)
    if nexthop is not None:
        hdr.nxt = nexthop
    else:
        hdr.nxt = -1
    return False

if __name__=='__main__':
    pass
