#!/usr/bin/env python
# 
# This script is the python version of the Content Router. Router class is
# modified based on Router class in vrouter.py. The idea reflected here should
# be further developed in the near future.
#
# REMARK: The topology used in this script is undirected graph.
# Usage:  prouter.py iport topology_file
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.28 created.
#

import re
import os
import sys
import time
import random
import string
import struct
import socket
import itertools
import threading
from multiprocessing import Manager, Queue

from common import *
from link import Link
from messageheader import *

OVERLAY_CMD = "vr|cmd"

class Router(object):
    def __init__(self, args):
        self.argsdict  = args                        # Keep a backup of args, other module may need it
        self.vrid      = args['vrid']                # The logical id instead of (ip,port)
        self.id        = self.generate_myid()
        self.ip        = args['ip']                  # ipv4 address, never use 127.0.0.1
        self.iport     = args['iport']               # port for incoming message
        self.routers   = set()
        self.manager   = Manager()
        self.rtable    = self.manager.dict()
        self.pathdict  = {}                          # a dict contains all the hops in each path
        self.topology  = {}                          # a dict contains all the links and link properties
        self.l2p       = args['l2p']                 # logical node to physical node
        self.ihandlers = [self.bypass_handler]
        self.logfh     = args['logfh']

        self.ibandwidth = args['ibandwidth']         # aggregated ingress bandwidth in bytes, zero means inf
        self.ebandwidth = args['ebandwidth']         # aggregated egress bandwidth in bytes, zero meas inf
        self.queuesize = 15000 if args['queuesize'] == 0 else args['queuesize']              # zero means inf
        self.queuepolicy = args['queuepolicy']       # queuing policy, a function reference
        self.iqueue = Queue(self.queuesize)          # SR processing limit is 15k pkts/s
        self.equeue = Queue(15000)                   # SR processing limit is 15k pkts/s
        self.cqueue = Queue(15000)                   # SR processing limit is 15k pkts/s
        pass

    def generate_myid(self):
        myid = ''.join( random.choice(string.ascii_uppercase + string.digits) for x in range(20) )
        return myid

    def cmd_handler(self, cmd, dst):
        """Handle the overlay command"""
        args = cmd.split("|")
        c = args[2]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if c == "ping":
            s.sendto("OK", dst)
        elif c == "l2pu":
            vrid  = int(args[3])
            ip    = args[4]
            iport = int(args[5])
            self.l2p[vrid] = (ip,iport)
        s.close()
        pass

    def read_topology_from_file(self, fn):
        """Read the overlay topology from a file, store link properties."""
        for line in open(fn, 'r').readlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            m = re.search(r"(\d+)\s*->\s*(\d+)\s*(\d*)\s*(\d*)\s*([.\d]*)\s*([.\d]*)", line).groups()
            vr1 = int(m[0])
            vr2 = int(m[1])
            weight = int(m[2]) if len(m[2]) else 1
            bandwidth = int(m[3]) if len(m[3]) and m[3] != '0' else float('Inf')
            delay = float(m[4]) if len(m[4]) else 0
            lossrate = float(m[5]) if len(m[5]) else 0
            self.routers.add(vr1)
            self.routers.add(vr2)
            link = tuple(sorted([vr1,vr2]))
            self.topology[link] = {'weight':weight, 'bandwidth':bandwidth,
                                   'delay':delay, 'lossrate':lossrate}
        pass

    def build_routing_table(self, src):
        """Use Dijkstra algorithm to find the shortest path."""
        Q = set(self.routers)
        dist = {}
        prev = {}
        for x in self.routers:
            dist[x] = 0 if src==x else float("Inf")
            prev[x] = None
        while len(Q):
            m = min( [(dist[x],x) for x in Q] )[1]
            if dist[m] == float("Inf"):
                break
            for n in self.neighbours(m):
                alt = dist[m] + self.weight(m,n)
                if alt < dist[n]:
                    dist[n] = alt
                    prev[n] = m
            Q.difference_update(set([m]))
        for x in self.routers:
            q = x
            while True:
                p = prev[q]
                if p == src or p == None:
                    self.rtable[x] = q
                    break
                else:
                    q = p
        pass

    def neighbours(self, src):
        """Given a specific node, return its neighbour set in the graph.
        Default value for src is router's own ID."""
        r = []
        for x, y in self.topology:
            if src == x:
                r.append(y)
            elif src == y:
                r.append(x)
        return r

    def weight(self, m, n):
        """Given two vertices, return the weight of corresponding edge."""
        link = tuple(sorted([m, n]))
        w = self.topology[link]['weight'] if link in self.topology else float("Inf")
        w = 0 if m==n else w
        return w

    def floyd_warshall(self, routers):
        """Use Floyd-Warshall algorithm to calculate the shortest path
        between any two nodes."""
        path = {}
        next = {}

        # Initialize
        for i, j in itertools.product(routers, repeat=2):
            path[(i, j)] = self.weight(i, j)

        for k in routers:
            for i in routers:
                for j in routers:
                    if path[(i, k)] + path[(k, j)] < path[(i, j)]:
                        path[(i, j)] = path[(i, k)] + path[(k, j)]
                        next[(i, j)] = k
        return path, next

    def fw_get_path(self, i, j, path, next):
        """Reconstruct the shortest path between two nodes, given the
        output from floyd_warshall algorithm."""
        if path[(i, j)]==float('Inf'):
            return None
        if not next.has_key((i, j)):
            return []
        itm = next[(i, j)]
        return self.fw_get_path(i, itm, path, next) + [itm] + self.fw_get_path(itm, j, path, next)

    def build_pathdict(self):
        """Reconstruct the shortest path between two nodes, given the
        output from floyd_warshall algorithm."""
        routers = sorted(self.routers)
        path, next = self.floyd_warshall(routers)
        for i, j in itertools.permutations(routers, 2):
            p = self.fw_get_path(i, j, path, next)
            self.pathdict[(i, j)] = [i] + p + [j]
        print self.vrid, ": pathdict construction done."
        pass

    def build_pathdict_my(self):
        """Liang: Obsolete"""
        routers = sorted(self.routers)
        for src, dst in itertools.combinations(routers, 2):
            if self.pathdict.has_key( (src,dst) ):
                continue
            for path in self.shortest_paths(src):
                if None in path:
                    continue

                for x, y in itertools.combinations(path, 2):
                    xi, yi = sorted([path.index(x), path.index(y)])
                    if not self.pathdict.has_key( (x,y) ):
                        subpath = list(path[xi:yi+1])
                        self.pathdict[(x,y)] = list(subpath)
                        subpath.reverse()
                        self.pathdict[(y,x)] = subpath
            print '# of paths:', len(self.pathdict)
        pass

    def build_pathdict_orig(self):
        """Liang: Obsolete"""
        routers = sorted(self.routers)
        for src, dst in itertools.combinations(routers, 2):
            if self.pathdict.has_key( (src,dst) ):
                continue
            for path in self.shortest_paths(src):
                if None in path:
                    continue

                # Guarantee the symmetric path
                for i in range(len(path)-1):
                    for j in range(i+2,len(path)):
                        x = path[i]
                        y = path[j]
                        if self.pathdict.has_key( (x,y) ):
                            for k in range(i+1,j):
                                # Liang: debug
                                #print k,self.pathdict[(x,y)], path
                                path[k] = self.pathdict[(x,y)][k-i]

                # Remark: the better way is using permutations here. However,
                # I take advantage of the default order used by combinations,
                # to save us some time.
                for x, y in itertools.combinations(path, 2):
                    xi = path.index(x)
                    yi = path.index(y)
                    if xi < yi and not self.pathdict.has_key( (x,y) ):
                        subpath = path[xi:yi+1]
                        self.pathdict[(x,y)] = list(subpath)
                        subpath.reverse()
                        self.pathdict[(y,x)] = subpath
            print '# of paths:', len(self.pathdict)
        pass

    def build_symmetric_routing_table(self, src):
        """The difference between this function and build_routing_table() is
        that this function guarantees the A -> B path and B -> A path are the
        same."""
        if not self.pathdict:
            self.build_pathdict()
        for dst in self.routers:
            path = self.pathdict.get((src,dst), None)
            if path is not None and len(path) > 1:
                self.rtable[dst] = path[1]
        pass

    def shortest_paths(self, src):
        """Use Dijkstra algorithm to find all shortest paths from the src."""
        paths = []
        Q = set(self.routers)
        dist = {}
        prev = {}
        for x in self.routers:
            dist[x] = 0 if src == x else float("Inf")
            prev[x] = None
        while len(Q):
            m = min( [(dist[x],x) for x in Q] )[1]
            if dist[m] == float("Inf"):
                break
            for n in self.neighbours(m):
                alt = dist[m] + self.weight(m, n)
                if (alt < dist[n]):
                    dist[n] = alt
                    prev[n] = m
            Q.difference_update(set([m]))
        for q in self.routers:
            tp = [q]
            while True:
                p = prev[q]
                tp.insert(0,p)
                if p == src or p == None:
                    break
                else:
                    q = p
            paths.append(tp)
        return paths

    def is_edge(self, src, dst):
        """Am I a edge-router?"""
        b = False
        if self.pathdict[(src,dst)][1] == self.vrid:
            b = True
        return b

    def bypass_handler(self, msg_hdr, router):
        """This hanlder is always the last handler in ihandlers.
        It distributes the packets into cqueue or equeue."""
        if msg_hdr.dst == self.vrid:
            self.cqueue.put(msg_hdr, True)
        else:
            self.equeue.put(msg_hdr, True)
        return True

    def register_ihandler(self, func):
        """Insert the func into the head of ihandlers array."""
        self.ihandlers.insert(-1, func)
        pass

    def start(self):
        """Start the routing service. Set up links to neighbours."""
        t0 = threading.Thread(target=self.service, args=())
        t0.deamon = True
        t0.start()

        t1 = threading.Thread(target=self.processor, args=())
        t1.daemon = True
        t1.start()

        t2 = threading.Thread(target=self.link_egress, args=())
        t2.daemon = True
        t2.start()

        for neighbour in self.neighbours(self.vrid):
            if self.vrid < neighbour:
                t = threading.Thread(target=self.setup_link, args=(neighbour,))
                t.daemon = True
                t.start()
                pass
        pass

    def service(self):
        """Listen on iport, accept incomming connections. For a new
        connection, the first 4 bytes indicate neighbor id."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind( ('', self.iport) )
        s.listen(1)
        while True:
            conn, addr = s.accept()
            neighbour = struct.unpack('!I', get_data(4, conn)[0])[0]
            link_property = self.topology[(neighbour, self.vrid)]
            tlink = Link(link_property, self.iqueue)
            self.l2p[neighbour] = {'addr':addr, 'link':tlink}
            tlink.setup(conn)
        pass

    def setup_link(self, neighbour):
        """Establish TCP connection to a neighbor. Each TCP connection
        corresponds to a physical link in the real-world."""
        addr = self.l2p[neighbour]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Liang: new feature
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        while True:
            try:
                time.sleep(random.randint(1,5))
                print "connecting to %s %s" % (str(neighbour), str(addr))
                s.connect(addr)
                s.send(struct.pack('!I', self.vrid))
                break
            except Exception, err:
                print "Exception:Router.setup_link():connect:", err

        link_property = self.topology[(self.vrid, neighbour)]
        tlink = Link(link_property, self.iqueue)
        self.l2p[neighbour] = {'addr':addr, 'link':tlink}
        tlink.setup(s)
        pass

    def send(self, msg_hdr):
        """Interface for the upperapp to send a message"""
        self.equeue.put(msg_hdr, True)
        pass

    def recv(self):
        """Interface for the upperapp to recv a message"""
        msg_hdr = self.cqueue.get(True)
        return msg_hdr

    def link_ingress(self, neighbour):
        """isolated"""
        pass

    def link_egress(self):
        """Process outgoing messages on a link. It checks whether the
        nexthop is set, set nexthop by using rtable if it is not set.
        Liang: REMARK: Now the upperapp bandwidth compete with egress, needs to be fixed, or NOT?"""
        tc = 0
        th = self.ebandwidth / 1.0
        t0 = time.time()
        t1 = t0
        while True:
            try:
                # aggregated egress traffic shaping
                t1 = time.time()
                if t1 - t0 < 1.0:
                    if tc >= th:
                        time.sleep(0.01)
                        continue
                else:
                    t0 = t1
                    tc = 0

                msg_hdr = self.equeue.get(True)
                tc += len(msg_hdr.data)

                nexthop = self.rtable[msg_hdr.dst] if msg_hdr.nxt < 0 else msg_hdr.nxt
                tlink = self.l2p[nexthop]['link']
                tlink.send(msg_hdr)
            except Exception, err:
                print "Exception:Router.link_egress():", self.vrid, err
        pass

    def processor(self):
        """Simulate the processor of a router, proecess message in the queue here."""
        tc = 0
        th = self.ibandwidth / 1.0
        t0 = time.time()
        t1 = t0

        while True:
            # aggregated ingress traffic shaping
            t1 = time.time()
            if t1 - t0 < 1.0:
                if tc >= th:
                    time.sleep(0.01)
                    continue
            else:
                t0 = t1
                tc = 0

            msg_hdr = self.iqueue.get(True)
            tc += len(msg_hdr.data)

            try:
                done = False
                for func in self.ihandlers:
                    try:
                        done = func(msg_hdr, self)
                    except Exception, err:
                        print 'Exception:processor:ihandlers:', self.vrid, err
                        self.logfh.write("EXCEPT:processor:ihandler:%s\n" % (str(err)))  # Liang: tmp use
                    if done:
                        break
            except Exception, err:
                print "Exception:Router.processor():", err
                self.logfh.write("EXCEPT:processor:%s\n" % (str(err)))  # Liang: tmp use
        pass

    pass

if __name__=="__main__":
    sys.exit(0)
