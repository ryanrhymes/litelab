#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
router module contains the implementation of overlay subsystem of
LiteLab.
"""

__version__ = '$Revision: 1253 $'
__author__ = 'Liang Wang <liang.wang@helsinki.fi>'
__date__ = '2011.09.09'
__credits__ = 'University of Helsinki'

import os
import sys
sys.path.append('/fs/home/lxwang/cone/lxwang/lib/python/')

print "Loading router Module"

import CacheStrategy


if __name__=="__main__":
    print sys.argv[0]
    sys.exit(0)
