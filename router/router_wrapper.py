#!/usr/bin/env python
# 
# This script is a wrapper of prouter.py. Since many ideas are not very mature
# to be adopted into the code. This wrapper is trying to keep the core code as
# clean as possible, and makes maintanence easier.
#
# Usage:  router_wrappper.py iport topology_file logdir cache_strategy
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.11 adopted from INCA project
#

import os
import sys
import signal
import fnmatch
from multiprocessing import *

from common import *
from prouter import *

def router_wrapper(args):
    signal.signal(signal.SIGTERM, clean_up)
    vrid   = args['vrid']
    ip     = args['ip']
    iport  = args['iport']
    tfile  = args['tfile']
    logdir = args['logdir']
    logfh  = open("%s/log-%i" % (logdir, args['vrid']), 'w')
    mycs   = None           # Caching theme used in the experiment
    cssz   = args['cssz']   # Cache size
    cstg   = args['cstg']   # Caching strategy
    crpl   = args['crpl']   # Cache replacement

    # Pre-process some parameters
    args['logfh'] = logfh
    args['ibandwidth'] = float('inf') if args['ibandwidth'] == 0 else args['ibandwidth']
    args['ebandwidth'] = float('inf') if args['ebandwidth'] == 0 else args['ebandwidth']
    if args['queuepolicy'] == 'none':
        args['queuepolicy'] = None
    else:
        exec('import QueuePolicy.%s as QP' % args['queuepolicy'])
        args['queuepolicy'] = QP.queue_policy

    # Initialize the router
    router = Router(args)

    # Build routing table
    router.read_topology_from_file(tfile)
    if args['rtable'] == 'otf':
        router.build_routing_table(router.vrid)
    elif args['rtable'] == 'sym':
        router.build_pathdict()
        router.build_symmetric_routing_table(vrid)
    elif os.path.exists(args['rtable']):
        router.pathdict = load_pathdict(args['rtable'])
        router.build_symmetric_routing_table(vrid)

    try:
        # Hook on different cache strategy
        if cstg.lower() not in ['', 'none']:
            mycs = hook_cache(router, cstg, cssz, crpl, logfh)
        if len(args['ihandler']) > 0:
            sys.path.append(args['ihandler'])
            hook_ihandler(router, args)
        router.start()
        if args['upperapp'] is not None:
            hook_upperapp(router, args)
    except Exception, err:
        logme(logfh, 0, ('prouter_wrapper',0), ('*',0), "EXCEPT", 0, '', str(err))

    bChecked = False
    ts = time.time()
    while True:
        try:
            time.sleep(0.5)
            if ( not bChecked and 
                 mycs is not None and 
                 mycs.cache.is_full() ):
                m = int((time.time()-ts)/60)
                logme2(logfh, 0, ('%im' % (m),0), ('*',0), "FULL", 0, '')
                bChecked = True
        except KeyboardInterrupt:
            break
        except Exception, err:
            logme(logfh, 0, ('prouter_wrapper',0), ('*',0), "EXCEPT", 1, '', str(err))
            pass

    pass

def hook_cache(router, cstg, cssz, crpl, logfh):
    """Hook on different cache strategy"""
    mycs = None

    # Load the corresponding cache strategy
    exec('from CacheStrategy.%s import *' % cstg)
    exec('from CacheStrategy.cache_%s import *' % crpl)

    # Hook on different admission & cooperative model: lru, cachedbit,
    # pcachedbit, pushcache, nbsearch, mhnbsearch, mfr, pushprob, smartre
    exec('mycs = %s(router, %i)' % (cstg, cssz))
    router.register_ihandler(mycs.ihandler)

    # Hook on different replacement model: lru, lfu, lfuda, fifobucket
    exec('mycs.cache = cache_%s(%i)' % (crpl, cssz))

    # Hook on log file handle
    if mycs is not None:
        mycs.logfh = logfh    
    return mycs

def hook_ihandler(router, args):
    """Hook on ihandlers and upperapp into the router"""
    idir = args['ihandler']
    ihs = sorted([ x for x in os.listdir(idir) if fnmatch.fnmatch(x, 'i_*.py') ])
    for ih in ihs:
        try:
            ih = ih[:-3]
            exec("from %s import ihandler" % ih)
            router.register_ihandler(ihandler)
        except Exception, err:
            print 'Exception:router_wrapper:hook_ihandler():', err
    pass

def hook_upperapp(router, args):
    """Start all the upperapp if there is any on this router"""
    for app, app_args in args['upperapp']:
        try:
            exec('from %s import main' % app)
            args['app_args'] = app_args
            p = Process(target=main, args=(router, args,))
            p.daemon = True
            p.start()
        except Exception, err:
            print 'Exception:router_wrapper:hook_upperapp():', err
    pass

def clean_up(signum, frame):
    """Handler for SIGTERM, do some cleaning tasks."""
    return sys.exit(0)


if __name__=='__main__':
    args = {}
    args['iport']  = int(sys.argv[1])
    args['tfile']  = sys.argv[2]
    args['logdir'] = sys.argv[3]
    args['logfh']  = open("%s/log-%i" % (logdir, args['vrid']), 'w')
    args['mycs']   = None                  # Caching theme used in the experiment
    args['cssz']   = int(sys.argv[4])      # Cache size
    args['cstg']   = sys.argv[5].lower()   # Caching strategy
    args['crpl']   = sys.argv[6].lower()   # Cache replacement
    router_wrapper(args)
    pass
