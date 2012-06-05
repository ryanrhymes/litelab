#!/usr/bin/env python
# 
# This script is adopted from INCA project. This script accecpts config file
# as an input argument. Load relevant information and starts the corresponding
# vrouters and their upper-level applications.
#
# REMARK: Currently, this script also starts the upper level application.
#         More complicated startup strategy will be introduced in future large
#         scale test.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.09 created
#

import re
import os
import sys
import time
import shlex
import socket

class ConfigReader(object):
    """This class read the config file, load necessary information."""
    def __init__(self, ifn):
        self.argsdict = {} # Other config args are saved in this dict
        self.argsdict['vrouter'] = ''
        self.argsdict['vrconf']  = ''
        self.argsdict['topology'] = ''
        self.argsdict['rtable'] = ''
        self.argsdict['ihandler'] = ''
        self.argsdict['upperapp'] = ''
        self.argsdict['appdict'] = {}
        self.argsdict['logdir'] = ''
        self.argsdict['cachestg'] = ''
        self.argsdict['cacherpl'] = ''
        self.argsdict['cachesize'] = 0
        self.argsdict['queuesize'] = 0
        self.argsdict['queuepolicy'] = 'fifo'
        self.argsdict['ibandwidth'] = 0
        self.argsdict['ebandwidth'] = 0
        lines = self.read_config(ifn)

        self.vrouters = self.get_vrouters(self.argsdict['topology'])
        self.upperapp = self.get_upperapp(self.argsdict['upperapp'])
        self.vrconf   = self.get_vrouter_configs(self.argsdict['vrconf'])

        self.vrdetail = {}
        self.assemble_config()

        # if the log dir doesn't exist, then create it!
        if not os.path.exists(self.argsdict['logdir']):
            try:
                os.makedirs(self.argsdict['logdir'])
            except Exception, err:
                print "Exception:ConfigReader:__init__():", err

        pass

    def read_config(self, ifn):
        """Read in the config file, eliminate the comments."""
        lines = []
        for line in open(ifn, "r").readlines():
            if line.startswith('#') or not len(line.strip()):
                continue
            else:
                lines.append(line)
                m = re.search(r'^\[(.*)\]:(.*)$', line)
                if m and len(m.groups()) > 1:
                    if 'appdict' == m.group(1):
                        n = re.search(r"([^=]+)=(.+)", m.group(2))
                        self.argsdict['appdict'][n.group(1)] = n.group(2)
                    else:
                        self.argsdict[m.group(1)] = m.group(2)
        return lines

    def assemble_config(self):
        """Assemble all the configs for routers and upper-level applications"""
        for vr in self.vrouters:
            try:
                vrid = int(vr)
                cachesize = self.argsdict['cachesize']
                cachestg = self.argsdict['cachestg']
                cacherpl = self.argsdict['cacherpl']
                queuesize = self.argsdict['queuesize']
                queuepolicy = self.argsdict['queuepolicy']
                ibandwidth = self.argsdict['ibandwidth']
                ebandwidth = self.argsdict['ebandwidth']
                ihandler = self.argsdict['ihandler']
                upperapp = self.upperapp[vrid] if vrid in self.upperapp.keys() else None
                if self.vrconf.has_key(vrid):
                    cachesize = self.vrconf[vrid]['cachesize']
                    cachestg  = self.vrconf[vrid]['cachestg']
                    cacherpl  = self.vrconf[vrid]['cacherpl']
                    queuesize = self.vrconf[vrid]['queuesize']
                    queuepolicy = self.vrconf[vrid]['queuepolicy']
                    ibandwidth  = self.vrconf[vrid]['ibandwidth']
                    ebandwidth  = self.vrconf[vrid]['ebandwidth']

                arg = {'vrid':   vrid,
                       'vrfile': self.argsdict['vrouter'],
                       'tfile': self.argsdict['topology'], 
                       'rtable': self.argsdict['rtable'],
                       'logdir': self.argsdict['logdir'],
                       'cssz': int(cachesize),
                       'cstg': cachestg,
                       'crpl': cacherpl,
                       'queuesize': int(queuesize),
                       'queuepolicy': queuepolicy,
                       'ibandwidth': int(ibandwidth),
                       'ebandwidth': int(ebandwidth),
                       'ihandler': ihandler,
                       'upperapp': upperapp
                       }

                self.vrdetail[vrid] = arg
            except Exception, err:
                print "Exception:ConfigReader.assemble_config():", err
                break
        pass

    def get_vrouters(self, ifn):
        """Read topology file, generate a set containing all the vrouters that
        should run on this node."""
        vset = set()
        # Get all the vrouters in the file, then filter
        for line in open(ifn, 'r').readlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            m = re.search(r"(\d+)\s*->\s*(\d+)\s*([.\d]*)\s*([.\d]*)", line).groups()
            vset.add(int(m[0]))
            vset.add(int(m[1]))
        return vset

    def get_vrouter_configs(self, ifn):
        """Return a dictionary containing the configurations for the routers
        in the experiment. The config in vrconf.txt will overwrite the overall
        config defined in config.txt."""
        vrconf = {}
        for line in open(ifn, 'r').readlines():
            if line.startswith('#') or not len(line.strip()):
                continue
            else:
                m = re.findall(r'(\S+)', line)
                vrid = int(m[0])
                cachesize = self.argsdict['cachesize'] if m[1]=='*' else m[1]
                cachestg = self.argsdict['cachestg']  if m[2]=='*' else m[2]
                cacherpl = self.argsdict['cacherpl']  if m[3]=='*' else m[3]
                queuesize = self.argsdict['queuesize']  if m[4]=='*' else m[4]
                queuepolicy = self.argsdict['queuepolicy']  if m[5]=='*' else m[5]
                ibandwidth = self.argsdict['ibandwidth']  if m[6]=='*' else m[6]
                ebandwidth = self.argsdict['ebandwidth']  if m[7]=='*' else m[7]
                vrconf[vrid] = {'cachesize':cachesize, 'cachestg':cachestg, 'cacherpl':cacherpl,
                                'queuesize':queuesize, 'queuepolicy':queuepolicy,
                                'ibandwidth':ibandwidth, 'ebandwidth':ebandwidth}
        return vrconf

    def get_upperapp(self, ifn):
        """Read User Application definition file, return user
        application on different routers in a dictionary."""
        apps = {}
        for line in open(ifn, 'r').readlines():
            if line.startswith('#') or not len(line.strip()):
                continue
            m = re.search(r"(\S+?)@(\S+?)\s(.*)", line)
            if m:
                app = m.group(1)
                vr  = int(m.group(2))
                arg = m.group(3)
                if vr in apps.keys():
                    apps[vr].append( (app,arg) )
                else:
                    apps[vr] = [(app,arg)]
        return apps

pass


if __name__=="__main__":
    config = ConfigReader(sys.argv[1])
    print config.get_vrouters(config.argsdict['topology'])
    sys.exit(0)
