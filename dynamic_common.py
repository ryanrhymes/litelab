#!/usr/bin/env python
# 
# This script contains some common structures and helper functions for
# other scripts.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.03
#

import os
import pickle
import re
import sys
import socket
import subprocess

def get_myip():
    """I have to use this trick to get the ipv4 address on UKKO node."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("google.com",80))
    return s.getsockname()[0]

def read_config(fn):
    """Given the config file, return a dictionary."""
    d = {}
    d['config_path'] = os.path.abspath(fn)

    for line in open(fn, "r").readlines():
        try:
            if line.startswith('#') or not len(line.strip()):
                continue

            # Fill in the argsdict
            m = re.search(r'^\[(.*)\]:(.*)$', line)
            if m and len(m.groups()) > 1:
                d[m.group(1)] = m.group(2)
        except Exception, err:
            print "Exception:read_config():", err

    return d

def dump_msg(msg):
    """Convert a msg into string message"""
    s = pickle.dumps(msg, pickle.HIGHEST_PROTOCOL)
    return s

def load_msg(s):
    """Load string message into object"""
    msg = pickle.loads(s)
    return msg


if __name__ == "__main__":
    print read_config(sys.argv[1])
    pass
