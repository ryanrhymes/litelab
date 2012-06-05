#!/usr/bin/env python
# 
# This script defines the Link class. Link class is an abstraction of
# a physical link. All the link properties, such as link weight,
# bandwidth, delay and loss rate are modelled in this class. Link
# class also maintains the connectivity of two SRouters.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.03.18 created.
#

import os
import sys
import time
import random
import socket
import struct
import threading
from multiprocessing import Queue

from common import *
from messageheader import *

class Link(object):
    """Link class is an abstraction of a physical link. All the link
    properties, such as link weight, bandwidth, delay and loss rate
    are modelled in this class. Link class also maintains the
    connectivity of two SRouters.
    le0, pe0 means logical and physical id of myelf; pe0: <ip, port>;
    le1, pe1 means logical and physical id of the other end."""

    def __init__(self, p, q):
        """Init a link based on input parameters. p is a dictionary
        contains following properties: weight: min val is 1;
        bandwidth: in bytes; delay: in seconds; lossrate: [0.0, 1.0]"""
        self.weight = p['weight']
        self.bandwidth = p['bandwidth']
        self.delay = p['delay']
        self.lossrate = p['lossrate']
        self.vr_iqueue = q
        self.iqueue = Queue(15000)
        self.equeue = Queue(15000)
        pass

    def setup(self, conn):
        """TCP connection already setup, link starts functioning"""
        t0 = threading.Thread(target=self.ingress, args=(conn,))
        t0.daemon = True
        t0.start()

        t1 = threading.Thread(target=self.egress, args=(conn,))
        t1.daemon = True
        t1.start()
        pass

    def ingress(self, conn):
        """Process incoming packets on the link. The link delay cannot
        be less than 10ms."""
        buf = ''
        tc = 0
        th = self.bandwidth / 1.0
        t0 = time.time()
        t1 = t0  # Time token for traffic shaping
        t2 = t0  # Time token for modeling delay
        delay = self.delay
        lossrate = self.lossrate

        while True:
            try:
                # Liang: link traffic shaping
                t1 = time.time()
                if t1 - t0 < 1.0:
                    if tc >= th:
                        time.sleep(0.01)
                        continue
                else:
                    t0 = t1
                    tc = 0

                length, buf = get_data(4, conn, buf)
                length = struct.unpack('!I', length)[0]
                data, buf = get_data(length, conn, buf)
                msg_hdr = MessageHeader()
                msg_hdr.recv(data)
                tc += len(msg_hdr.data)

                # Liang: Model link properties here.
                if delay > 0:
                    if time.time() - t2 > delay:
                        time.sleep(delay)
                    t2 = time.time()

                if lossrate > 0:
                    if random.random() < lossrate:
                        #self.logfh.write("loss\n")
                        #self.logfh.flush()
                        continue

                # Liang: Apply queueing policy here.
                #if qp is not None and not qp(None):
                #    continue

                self.vr_iqueue.put(msg_hdr, True)
            except Exception, err:
                print "Exception:Link.ingress():", err
                #self.logfh.write("EXCEPT:ingress:%s\n" % (str(err)))  # Liang: tmp use
                if len(buf) == 0:
                    break

        pass

    def egress(self, conn):
        """Process outgoing packets on the link."""
        while True:
            try:
                msg_hdr = self.equeue.get(True)
                send_frame(conn, msg_hdr)
            except Exception, err:
                print "Exception:Link.egress():", err
        pass

    def send(self, msg_hdr):
        """Put a packet into egress queue, interface to SRouter."""
        self.equeue.put(msg_hdr, True)
        pass

    pass


if __name__=="__main__":
    sys.exit(0)
