#!/usr/bin/env python
# 
# This script implements a class which report the node stats.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.06
#

import os
import re
import subprocess
import sys

class NodeStat(object):
    def __init__(self):
        self.metric = self.get_metric()
        pass

    def get_cpu_load(self):
        s = subprocess.Popen("uptime", stdout=subprocess.PIPE).communicate()[0]
        cpu_load = re.search(r"load average: (.+?),", s).groups()[0]
        cpu_load = float(cpu_load)
        return cpu_load

    def get_metric(self):
        cpu_load = self.get_cpu_load()
        metric = cpu_load
        return metric

    pass

if __name__=="__main__":
    stat = NodeStat()
    print stat.metric
