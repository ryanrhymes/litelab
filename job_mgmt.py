#!/usr/bin/env python
# 
# This script implements a class which manages all the jobs in LiteLab.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.04.17 created
#

import os
import re
import sys
import time
import pickle
import threading
from multiprocessing import *
from dynamic_common import *

class JobMgmt(object):
    def __init__(self):
        self.jobs = {}
        self.logfn = '%s/log_job.txt' % os.path.dirname(os.path.realpath(__file__))
        pass

    def add_job(self, jobid, config_fn, nodes):
        self.jobs[jobid] = {'timestamp':time.ctime(), 'config':config_fn, 'nodes':nodes}
        pass

    def delete_job(self, jobid):
        if self.jobs.has_key(jobid):
            self.jobs.pop(jobid)
        pass

    def update_stat(self):
        logh = open(self.logfn, 'wb+')
        for jobid, v in self.jobs.items():
            logh.write('%s\t%i\t%s\t%s\n' % 
                       (v['timestamp'], jobid, v['config'], str(sorted(v['nodes']))))
            pass
        logh.close()
        pass

    pass


if __name__=="__main__":

    sys.exit()
