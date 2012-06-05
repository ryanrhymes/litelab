#!/usr/bin/env python
# 
# This module contains various queueing policies you can hook into prouter,
# such as FIFO, AQM, RED, WRED and so on. New policy can be added into this
# module. Use the policy name as your file name, in lowercase, which should
# be consistent with the one used in router config file. In the new policy
# file, implement queue_policy(args) function.
#
# None means no queueing policy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.02.02 created
#

import os
import sys

print "Loading QueuePolicy Module"
sys.path.append('/fs/home/lxwang/cone/lxwang/litelab/router/')
sys.path.append('/fs/home/lxwang/cone/lxwang/overlay/lib/')

if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
