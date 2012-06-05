#!/usr/bin/env python
# 
# This script contains some common structures and helper functions for
# prouter.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.28 created, 2011.06.10 modified.
#

import re
import os
import sys
import time
import bisect
import random
import struct
import socket
import hashlib
import binascii
import pickle
from ctypes import *

from messageheader import *

# Some global varialbes
RETRYNUM    = 3
UDPTIMEOUT  = 2
DIGEST_LEN  = 20
PACKET_LEN = 128*2**10
CHUNK_LEN   = 2**10

def get_myip():
    """I have to use this trick to get the ipv4 address on UKKO node."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("google.com",80))
    return s.getsockname()[0]

def get_ipaddr_list(iaddrs):
    """This function accepts an array of strings in the format of ip:port,
    change it into (ip,port) form, and return the array."""
    oaddrs = []
    for x in iaddrs:
        y = x.split(':')
        oaddrs.append( (y[0],int(y[1])) )
    return oaddrs

def get_iport():
    """Try to get three available ports on the local node"""
    iport = None
    while not iport:
        try:
            iport = random.randint(20000, 60000)
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock1.bind(("", iport))
            sock2.bind(("", iport+1))
            sock3.bind(("", iport+2))
        except Exception, err:
            print "Exception:common.py:get_iport():", err
            iport = None
        finally:
            sock1.close()
            sock2.close()
            sock3.close()
    return iport

def get_server_list(s):
    """Pick all server's vrid in the input list"""
    servers = []
    try:
        servers = [int(x) for x in re.findall(r'\$(\d+)', s)]
    except Exception, err:
        print "Exception:common.py:get_server_list():", err
    return servers

def create_metafile(ifn, ofn):
    """Given the input file, create meta file for it, use sha1."""
    ifh = open(ifn, 'rb')
    ofh = open(ofn, 'wb')
    while True:
        chunk = ifh.read(CHUNK_LEN)
        if chunk:
            sha1 = hashlib.sha1()
            sha1.update(chunk)
            ofh.write(sha1.digest())
            pass
        else:
            break
    ifh.close()
    ofh.close()
    pass

def load_metafile(ifn):
    """Given the metafile, load all the ids into a list."""
    id_list = []
    meta = open(ifn, 'rb')
    while True:
        s = meta.read(DIGEST_LEN)
        if s:
            id_list.append(s)
        else:
            break
    return id_list

def load_file(ifn):
    """Given the file, create key for each chunk and load all the (key,chunk)
    pair into a dict."""
    id_dict = {}
    ifh = open(ifn, 'rb')
    while True:
        chunk = ifh.read(CHUNK_LEN)
        if chunk:
            sha1 = hashlib.sha1()
            sha1.update(chunk)
            id_dict[sha1.digest()] = chunk
            pass
        else:
            break
    return id_dict

def logme(ifh, seq, src, dst, msgtype, hit, cid, hops):
    if ifh:
        ts = time.time()
        ifh.write("%f\t%i\t%s\t%s\t%s\t%i\t%s\t%s\n" % 
                  (ts,seq,str(src),str(dst),msgtype,hit,binascii.hexlify(cid),hops))
        ifh.flush()
    pass

def logme2(ifh, seq, src, dst, msgtype, hit, cid):
    if ifh:
        ts = time.time()
        ifh.write("%f\t%i\t%s\t%s\t%s\t%i\t%s\n" % 
                  (ts,seq,str(src),str(dst),msgtype,hit,binascii.hexlify(cid)))
        ifh.flush()
    pass

def logtimetoken(ifn, info=''):
    """This is a tentative solution for excluding entries in warm-up phase."""
    ifh = open(ifn, 'a')
    ifh.write("%f\t%s\n" % (time.time(),info) )
    ifh.close()
    pass

def pmf_uniform(ids, llen):
    """Uniform distribution"""
    rlist = []
    for i in range(llen):
        rid = random.choice(ids)
        rlist.append(rid)
    random.shuffle(rlist)
    return rlist

def pmf_zipf(ids, llen):
    """Zipfan distribution"""
    rlist = []
    hotnum = int(llen*0.1)
    i = 1
    while True:
        freq = int(hotnum/i)
        if freq == 0:
            freq = 1
        rlist += [ (i, ids[i]) ]*freq
        if len(rlist) >= llen:
            break
        i += 1
    random.shuffle(rlist)
    return rlist

def request_pattern_zipf(ids, llen, s=0.9):
    """Use Zipfan distribution to model request pattern."""
    rlist = []
    plist = []
    n = len(ids)
    h = 0.0
    for x in range(n):
        h += 1.0/( (x+1)**s )
        plist.append(h)

    while len(rlist) < llen:
        r = random.uniform(0.0, h)
        i = bisect.bisect_left(plist,r)
        i = i if i<n else n-1
        rlist.append( (i, ids[i]) )
    return rlist

def request_pattern_zipf_test(ids, llen, s=0.9):
    """This is a test zipfan request pattern."""
    rlist = []
    plist = []
    random.shuffle(ids)
    n = len(ids)
    h = 0.0
    for x in range(n):
        h += 1.0/( (x+1)**s )
        plist.append(h)

    while len(rlist) < llen:
        r = random.uniform(0.0, h)
        i = bisect.bisect_left(plist,r)
        i = i if i<n else n-1
        rlist.append( (i, ids[i]) )
    return rlist

def request_pattern_customize(ids, llen):
    """Generate customized request pattern, for test purpose."""
    rlist = []
    i = 0
    while len(rlist) < llen:
        rlist.append( (i, ids[i]) )
        i = (i + 1) % len(ids)
    return rlist

def get_data(length, conn, buf = ''):
    """Receive the specified length of data from the link"""
    while len(buf) < length:
        tbuf = conn.recv(PACKET_LEN)
        buf += tbuf
        if len(tbuf) == 0:
            break
    rdata = buf[0:length]
    buf = buf[length:]
    return rdata, buf

def send_frame(conn, msg_hdr):
    data = msg_hdr.send()
    length = struct.pack('!I', len(data))
    conn.send(length + data)
    pass

def hash_header(hdr):
    """Hash message header into (0,1) interval"""
    s = str(hdr.src) + str(hdr.dst) + str(hdr.seq)
    s = hashlib.md5(s).digest()
    x = long(s.encode('hex'), 16)
    y = 2**128
    h = 1.0 * x / y
    h = c_float(h).value  # Liang: This is important!
    return h

# Liang: debug, please remove this function
def gget_manifest(ifn):
    """LP solution, needs to be fixed."""
    manifest = {}

    manifest[1] = {}
    manifest[1]['path'] = [0, 1, 2, 3, 5]
    manifest[1][1] = {'range': (0.0, 0.2), 'quota': 100}
    manifest[1][2] = {'range': (0.2, 0.5), 'quota': 100}
    manifest[1][3] = {'range': (0.5, 0.7), 'quota': 100}

    manifest[2] = {}
    manifest[2]['path'] = [0, 1, 2, 4, 6]
    manifest[2][1] = {'range': (0.0, 0.1), 'quota': 100}
    manifest[2][2] = {'range': (0.1, 0.4), 'quota': 100}
    manifest[2][4] = {'range': (0.4, 1.0), 'quota': 100}

    return manifest

def get_manifest(ifn):
    """LP solution, needs to be fixed."""
    manifest = pickle.Unpickler(open(ifn, "r")).load()
    return manifest

def get_bucket_quota(manifest, vrid):
    """Given the router id and manifest, get the bucket quota for each path"""
    bucket_quota = []
    for pathid, v in manifest.items():
        # Check if I am an Ingress
        if vrid == v['path'][0]:
            for router in v['path'][1:-1]:
                bucket_quota.append( (pathid, router, v[router]['quota']) )
        # Check if I am an Interior
        elif vrid in v.keys():
            bucket_quota.append( (pathid, vrid, v[vrid]['quota']) )
    return bucket_quota

def get_pathid_dict(manifest):
    """Given the manifest, return the dict for pathid."""
    pathid_dict = {}
    for pathid, v in manifest.items():
        server = v['path'][0]
        client = v['path'][-1]
        pathid_dict[(server, client)] = pathid
    return pathid_dict

def get_overlapmatrix(manifest):
    """Generate the overlapmatrix given manifest"""
    matrix = {}
    for path_i in manifest.keys():
        matrix[path_i] = {}
        for path_j in manifest.keys():
            routers_i = manifest[path_i]['path'][1:-1]
            routers_j = manifest[path_j]['path'][1:-1]
            overlap = -1.0
            for x in range(min(len(routers_i), len(routers_j))):
                if routers_i[x] == routers_j[x]:
                    overlap = manifest[path_j][routers_j[x]]['range'][1]
                else:
                    break
            # Only store those with same ingress in order to reduce space
            if overlap > 0.0:
                matrix[path_i][path_j] = overlap
    return matrix

def load_overlapmatrix(ifn):
    """Load the overlapmatrix from the specified file"""
    overlapmatrix = pickle.Unpickler(open(ifn, "r")).load()
    return overlapmatrix

def get_coveredrange(manifest, pathid):
    """Give the manifest and the pathid, calculate """
    last_router = manifest[pathid]['path'][-2]
    rng = manifest[pathid][last_router]['range'][1]
    return rng

def get_responsible_router(manifest, pathid, header_hash):
    """Find out which router is responsible for caching this packet"""
    router = None
    for r in manifest[pathid]['path'][1:-1]:
        rng = manifest[pathid][r]['range']
        if rng[0] <= header_hash and header_hash < rng[1]:
            router = r
            break
    return router

def load_pathdict(ifn):
    """Load router's pathdict from a specified file"""
    pathdict = pickle.Unpickler(open(ifn, "r")).load()
    return pathdict


if __name__=="__main__":
    get_iport()
    print sys.argv[0]
    sys.exit(0)
