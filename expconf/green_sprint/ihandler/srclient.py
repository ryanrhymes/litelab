#!/usr/bin/env python
# 
# This script is python version of the client in INCA experiment.
# It submits requests to the given server with certain pattern.
#
# usage: client.py
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.02.27 created.
#

import os
import sys
import time
import random
import struct
import threading

sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/')
from common import *
from messageheader import *

EXPTIME = 180 # Experiment time in logic hour
TFACTOR = 30  # Expansion factor in seconds
TALIGNMENT = 100 # alignement for startup time.
# Request rate in each logic hour
#REQRATE = [9, 8.5, 8, 8, 8, 8, 7.5, 7.5, 7, 6.5, 6, 5.5, 5, 5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 8.5, 9]
REQRATE = [5, 5, 5] 
#REQRATE = [2, 2, 2, 2, 2, 4, 7, 13, 24, 30, 30, 20, 10, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]


class Client(object):
    def __init__(self, vrid, router, args, logfh=None):
        self.vrid     = vrid              # the vrid of the router this client running on
        self.logfh    = logfh
        self.router   = router
        self.args     = args

        self.seq  = random.randint(0,9999999)
        metafile= args['app_args'].split()[0]
        self.cids = load_metafile(metafile)
        self.reqs = [] #request_pattern_zipf(self.cids, 10000)
        self.servers = get_server_list(args['app_args'])

        pass

    def __del__(self):
        pass

    def start_receive(self):
        """Receiving process in Client, handle incoming responses."""
        c = 0
        tc = 0
        t0 = time.time()
        t1 = t0
        while True:
            try:
                hdr = self.router.recv()
                if hdr.type != MessageType.RESPONSE:
                    continue

                c += 1
                tc += len(hdr.data)
                t1 = time.time()
                if t1 - t0 >= 1.0:
                    print "speed:%.2f KiB/s,\treceive:%i" % ((tc / (t1 - t0)) / 2**10, c)
                    t0 = t1
                    tc = 0

                #print "%i: receve msg %i (%iB)" % (c, hdr.seq, len(hdr.data))
                logme(self.logfh, hdr.seq, hdr.src, hdr.dst, "RSP", hdr.hit, hdr.id, hdr.hop)
            except Exception, err:
                print "Exception:Client.start_receiving():", err
                logme(self.logfh, 0, '*', '*', "EXCEPT", 0, '*', str(err))
        pass

    def start_request(self):
        t_start = time.time()
        t_stop = t_start + EXPTIME * TFACTOR

        while time.time() < t_stop:
            try:
                if len(self.reqs) == 0:
                    self.reqs = request_pattern_zipf(self.cids, 10000)
                index, cid = self.reqs.pop(0)
                sid = random.randint(0, len(self.servers) - 1)
                self.seq += 1
                self.request(self.seq, cid, self.servers[sid])

                # Liang: debug, this is a trade-off now. Should be fixed in future.
                ti = int((time.time() - t_start) / TFACTOR) % len(REQRATE)
                ts = 1.0 / REQRATE[ti]
                time.sleep(ts)
            except Exception, err:
                print "Exception:Client.start_request():", err

        # Task done, wait for the receiving thread
        while True:
            time.sleep(1)
        print "Client: quit..."
        pass

    def request(self, seq, cid, server):
        """Request a single chunk"""
        hdr = MessageHeader()
        hdr.type = MessageType.REQUEST
        hdr.id = cid
        hdr.seq = seq
        hdr.src = self.vrid
        hdr.dst = server
        hdr.hit = 0
        hdr.hop = 1
        self.router.send(hdr)
        pass

    def start(self):
        """Start the client, both request and receive threads"""
        t0 = threading.Thread(target=self.start_receive)
        t0.daemon = True
        t0.start()

        t1 = threading.Thread(target=self.start_request)
        t1.daemon = True
        t1.start()

        while True:
            time.sleep<(1)
        pass

    pass


def main(router, args):
    vrid   = args['vrid']
    logdir = args['logdir']
    logfh  = open("%s/client-%i" % (logdir, vrid), 'w')
    client = Client(vrid, router, args, logfh)

    time.sleep(15)
    time.sleep((int(time.time()) / TALIGNMENT) * TALIGNMENT + 2 * TALIGNMENT - time.time())
    client.start()
    pass


if __name__=="__main__":
    sys.exit(0)
