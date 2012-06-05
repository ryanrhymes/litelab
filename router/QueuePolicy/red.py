#!/usr/bin/env python
# 
# This script implements the RED(RFC2309) queueing policy.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.02.02 created
#

import os
import sys
import random

def queue_policy(args):
    enqueue = True
    if random.random() < 0.5:
        enqueue = False
    return enqueue


if __name__ == "__main__":
    sys.exit(0)
