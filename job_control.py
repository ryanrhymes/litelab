#!/usr/bin/env python
# 
# This script implements a class which manages all the tasks allocated
# on a physical node.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.09 created.
#

import os
import re
import sys
import time
import pickle
import threading
from multiprocessing import *
from dynamic_common import *
import router
from router.router_wrapper import *

BPORT = 2011

class JobControl(object):
    def __init__(self, jobid):
        self.jobid = jobid
        self.state = ''  # state a of job: INIT|READY|RUN|PAUSE|STOP
        self.vrdict = {}  # Mapping from logical node to (ip,port)
        self.vr_process = {}
        self.vr_lock = threading.Lock()  # Protect vrdict and vr_process
        self.done = threading.Event()
        t = threading.Thread(target=self.watcher, args=())
        t.daemon = True
        t.start()
        pass

    def create_router(self, args):
        """Create a router without running it."""
        args['ip'] = router.common.get_myip()
        args['iport'] = router.common.get_iport()
        args['l2p'] = self.vrdict

        self.vr_lock.acquire()
        self.vrdict[args['vrid']] = (args['ip'],args['iport'])
        p = Process(target=router_wrapper, args=(args,))
        self.vr_process[args['vrid']] = (args,p)
        self.vr_lock.release()

        return p

    def remove_router(self, vrid):
        """Remove a router given its vrid"""
        self.vr_lock.acquire()
        if vrid in self.vrdict.keys():
            self.vrdict.pop(vrid)
        if vrid in self.vr_process.keys():
            try:
                _, p = self.vr_process.pop(vrid)
                p.terminate()
            except Exception, err:
                print "Exception:JobControl.remove_router():", err
        self.vr_lock.release()
        pass

    def __del__(self):
        self.terminate()
        pass

    def get_unknown_vr(self):
        """Scan vrdict, return those vrid without corresponding (ip,port)"""
        unknown = set()
        self.vr_lock.acquire()
        for k,v in self.vrdict.items():
            if self.vrdict[k] is None:
                unknown.add(str(k))
        self.vr_lock.release()
        return unknown

    def reply_vrdict_query(self, qlist):
        """Reply the queries for mapping from logic node to physic node."""
        replies = {}
        for q in qlist:
            q = int(q)
            self.vr_lock.acquire()
            if q in self.vrdict.keys() and self.vrdict[q]:
                replies[q] = self.vrdict[q]
            self.vr_lock.release()
        return replies

    def set_vrdict(self, vrset):
        """Load router set into an empty vrdict"""
        self.vr_lock.acquire()
        for vr in vrset:
            if vr not in self.vrdict.keys():
                self.vrdict[vr] = None
        self.vr_lock.release()
        pass

    def start_job(self):
        """Start the job, which means starting all the apps in the job."""
        self.vr_lock.acquire()
        for vrid, v in self.vr_process.items():
            args, p = v
            if not p.is_alive():
                p.start()
        self.vr_lock.release()
        pass

    def terminate(self):
        """Terminate this job and all its related child processes"""
        self.vr_lock.acquire()
        for k in self.vr_process.keys():
            _, p = self.vr_process.pop(k)
            p.terminate()
            # Liang: temp banned, it seems I cannot start following processes if I use this. Can not figure out the reason at the moment.
            # os.waitpid(p.pid, 0)
        self.vr_lock.release()        
        self.done.set()
        pass

    def update_vrdict(self, args):
        """Update an item in vrdict"""
        self.vr_lock.acquire()
        for vrid, v in args.items():
            ip, iport = v
            self.vrdict[vrid] = (ip,iport)
        self.vr_lock.release()
        pass

    def update_l2p(self, vrid, ip, iport):
        """Update the l2p tables of all the routers and app"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = "vr|cmd|l2pu|%i|%s|%i" % (vrid, ip, iport)
        self.vr_lock.acquire()
        for args,_ in self.vr_process.values():
            try:
                addr = (args['ip'], args['iport'])
                sock.sendto(msg, addr)
            except Exception, err:
                print "Exception:JobControl.update_l2p():", err
        self.vr_lock.release()           
        pass

    def watcher(self):
        """Keep checking the JobControl status"""
        bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while not self.done.is_set():
            try:
                print "job", self.jobid, "state", self.state
                if self.state == "INIT":
                    unknown = self.get_unknown_vr()
                    if len(unknown) > 0:
                        msg = dump_msg({'op':'jobq', 'jobid':self.jobid, 'args':unknown,
                                        'tid':random.randint(0, 65535)})
                        bsock.sendto(msg, ("<broadcast>", BPORT))
                    else:
                        self.state = "READY"
                elif self.state == "READY":
                    self.start_job()
                    self.state = "RUN"
                time.sleep(1)
                # Liang: debug
                print "??? unknown:", len(unknown), "vr_process:", len(self.vr_process)
            except Exception, err:
                print "Exception:JobControl.watcher():", err
        pass

    pass


if __name__=="__main__":
    my_controller = JobControl()
    p = Process(target=my_controller.start_router, args=(None,))
    p.start()

    time.sleep(10)
    p.terminate()

    print "end"
    sys.exit()
