#!/usr/bin/env python
# 
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2015.02.16 created.
#

import os
import sys


def load_mapping(ifn):
    d = {}
    for line in open(ifn, 'r'):
      x, y  = [ int(x) for x in line.strip().split() ]
      d[y] = x
    return d


def load_traffic(ifn):
    a = [[],[],[]]
    for line in open(ifn, 'r'):
      src, dst, trf  = [ x for x in line.strip().split() ]
      a[0].append(int(src))
      a[1].append(int(dst))
      a[2].append(float(trf))
    return a

def mapping(d, a):
    mt = min(a[2])
    for i in xrange(len(a[0])):
        src = d[a[0][i]]
        dst = d[a[1][i]]
        trf = int(a[2][i] / mt)
        print "%i %i %i" % (src, dst, trf)
    pass

if __name__=='__main__':
    d = load_mapping(sys.argv[1])
    a = load_traffic(sys.argv[2])
    mapping(d, a)

    sys.exit(0)
