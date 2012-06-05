#!/usr/bin/env python
# 
# This module contains various caching strategies. All the strategies will be
# tested on the overlay. Each class in this module should at least implement
# ihandler and ehandler interface.
#
# Remark: log function looks ugly currently due to performance concern. Needs
#         higher abstraction.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.05.29 created
#

import os
import sys

print "Loading CacheStartegy Module"
sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/')
sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/CacheStrategy/')

if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
