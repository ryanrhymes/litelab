#!/usr/bin/env python
# 
# This script implement GreenMap class as User Application for LiteLab
#
# usage: green.py
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.03.21 created
#

import os
import sys
import time
import threading
from multiprocessing import Manager, Queue

sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/')
from common import *
from messageheader import *

TIME_SCALE = 30  # time scale factor in seconds
TALIGNMENT = 100 # alignement for startup time.

class GreenMap(object):
    """GreenMap class not only reads config file, and updates routing table,
    but also reads in green ratio."""

    def __init__(self, router, args):
        self.router = router
        self.args = args
        appsfn, gtfn, gmfn = args['app_args'].split()

        self.init_rtable()
        self.tmst = (int(time.time()) / TALIGNMENT) * TALIGNMENT + 2 * TALIGNMENT  # Liang: this is beautiful!
        self.green_rt = self.get_green_table(gtfn)
        self.get_green_map(gmfn)
        self.logfh = None
        pass

    def get_green_map(self, ifn):
        """Load green ratio map into the dictionary"""
        tmst = int(self.tmst) / TIME_SCALE
        d = {}
        for line in open(ifn, 'r').readlines():
            try:
                m = re.search(r'(\S+)\s+(\S+)\s+(\S+)\s*', line).groups()
                node = int(m[0])
                tm = tmst + int(m[1])
                gr = float(m[2])
                if not d.has_key(node):
                    d[node] = {}
                d[node][tm] = gr
            except Exception, err:
                print "Exception:get_green_map()", err
        for node in d.keys():
            self.router.greenmap[node] = d[node]
        pass

    def get_green_table(self, ifn):
        """Return the changes in routing table according to the green
        energy dynamics."""
        green_rt = []
        tmst = self.tmst
        for line in open(ifn, 'r').readlines():
            try:
                m = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*', line).groups()
                m = [ int(x) for x in m ]
                tm, src, dst, node, nexthop = m
                if node != self.router.vrid:
                    continue
                if tm == 0:
                    self.router.rtable[(src, dst)] = nexthop
                    continue
                m[0] = tmst + tm * TIME_SCALE
                green_rt.append(m)
            except Exception, err:
                print "Exception:get_green_table()", err
        return green_rt

    def init_rtable(self):
        """Initialize the router rtable based on the pathdict."""
        for k, v in self.router.pathdict.items():
            try:
                if self.router.vrid not in v:
                    self.router.rtable[k] = None
                else:
                    ti = v.index(self.router.vrid)
                    self.router.rtable[k] = v[ti + 1]
            except Exception, err:
                print "Exception:init_rtable()", err
        pass

    def refresh_rtable(self):
        self.logfh.write('start on %4i:\t%.2f\n' % (self.router.vrid, time.time()))
        while len(self.green_rt):
            try:
                tss = max(0.01, self.green_rt[0][0] - time.time())
                time.sleep(tss)
                tsn = time.time()
                print self.router.vrid, ": Update Routing Table ..."
                self.logfh.write('%.2f\t%.2f\n' % (tsn, self.green_rt[0][0]))
                self.logfh.flush()

                for m in list(self.green_rt):
                    tm, src, dst, node, nexthop = m
                    if tm <= tsn:
                        self.router.rtable[(src, dst)] = nexthop
                        self.green_rt.remove(m)
                    else:
                        break
                pass
            except Exception, err:
                print "Exception:GreenMap.refresh_rtable():", err
                self.logfh.write('Exception:%s\n', str(err))
        pass

    pass


def main(router, args):
    """Router will call this function"""
    vrid   = args['vrid']
    logdir = args['logdir']
    ifn    = args['app_args']

    time.sleep(15)

    green = GreenMap(router, args)
    green.logfh = open("%s/green-%i" % (logdir, vrid), 'w')
    green.refresh_rtable()
    pass


if __name__=="__main__":
    sys.exit(0)
