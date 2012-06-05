#!/usr/bin/env python
# 
# This script implement Green class as User Application for LiteLab
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

class Green(object):
    """Green class reads config file, and updates routing table """

    def __init__(self, router, args):
        self.router = router
        self.args = args
        appsfn, gtfn = args['app_args'].split()
        self.emap = self.get_edge_mapping(appsfn)
        self.green_rt = self.get_green_table(gtfn)
        self.logfh = None
        pass

    def get_edge_mapping(self, ifn):
        """Return a mapping from client/server to its edge router."""
        emap = {}
        server = []
        client = []
        for line in open(ifn, 'r').readlines():
            try:
                m = re.search(r'(\S+)@(\d+)', line).groups()
                if 'server' in m[0]:
                    server.append(int(m[1]))
                elif 'client' in m[0]:
                    client.append(int(m[1]))
            except Exception, err:
                print "Exception:append_endpoints()", err

        tvid = self.router.vrid
        for nid in server + client:
            try:
                edge_vrid = self.router.pathdict[(nid, tvid)][1]
                emap[edge_vrid] = nid
            except Exception, err:
                print "Exception:Green.get_edge_mapping():", err
        return emap

    def get_green_table(self, ifn):
        """Return the changes in routing table according to the green
        energy dynamics."""
        green_rt = []
        tmst = (int(time.time()) / TALIGNMENT) * TALIGNMENT + 2 * TALIGNMENT  # Liang: this is beautiful!
        for line in open(ifn, 'r').readlines():
            try:
                m = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*', line).groups()
                m = [ int(x) for x in m ]
                tm, src, dst, node, nexthop = m
                if node != self.router.vrid or tm == 0:
                    continue
                m[0] = tmst + tm * TIME_SCALE
                green_rt.append(m)
            except Exception, err:
                print "Exception:get_green_table()", err
        return green_rt

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
                        self.router.rtable[dst] = nexthop
                        if self.emap.has_key(dst):
                            ept = self.emap[dst]
                            self.router.rtable[ept] = nexthop
                        self.green_rt.remove(m)
                    else:
                        break
                pass
            except Exception, err:
                print "Exception:Green.refresh_rtable():", err
                self.logfh.write('Exception:%s\n', str(err))
        pass

    pass


def main(router, args):
    """Router will call this function"""
    vrid   = args['vrid']
    logdir = args['logdir']
    ifn    = args['app_args']

    time.sleep(15)

    green = Green(router, args)
    green.logfh = open("%s/green-%i" % (logdir, vrid), 'w')
    green.refresh_rtable()
    pass


if __name__=="__main__":
    sys.exit(0)
