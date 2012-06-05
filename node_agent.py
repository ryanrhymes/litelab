#!/usr/bin/env python
# This script implements a node agent running on each node within a cluster.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.09.03 created
#

import bisect
import os
import random
import socket
import subprocess
import sys
import time
import threading
from dynamic_common import *
from config_reader import ConfigReader
from job_control import JobControl
from job_mgmt import JobMgmt
from node_stat import NodeStat

BPORT = 2011
PACKAGE_LEN = 64*2**10

class Agent(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.agents = {}
        self.id = random.randint(0, 65535)
        self.ip = get_myip()
        self.stat = NodeStat()
        self.exit_event = threading.Event()
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        self.jmgmt = None

        t = threading.Thread(target=self.probe, args=())
        t.daemon = True
        t.start()
        pass

    def broadcast(self, msg):
        msg['tid'] = random.randint(0, 65535)
        msg = dump_msg(msg)
        bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        bsock.sendto(msg, ("<broadcast>", BPORT))
        pass

    def get_app_path(self):
        app_path = os.path.realpath(__file__)
        return app_path

    def get_config_dir(self):
        config_dir = "%s/config" % os.path.dirname(self.get_app_path())
        return config_dir

    def get_idle_nodes_origin(self):
        l = []
        for k, v in self.agents.items():
            agip, agts, agcpu = v
            bisect.insort_left(l,(agcpu,agip))
        l.sort()
        return l

    def get_idle_nodes(self):
        """Liang: Only used in debug version, replace with original
        one in product version."""
        if not hasattr(self, 'agent_in_use'):
            self.agent_in_use = set()
        l = []
        for k, v in self.agents.items():
            agip, agts, agcpu = v
            if agip in self.agent_in_use:
                continue
            else:
                bisect.insort_left(l,(agcpu,agip))
        l.sort()
        return l

    def get_jobcontrol(self, jobid):
        """Get job control object from self.jobs"""
        jc = None
        self.jobs_lock.acquire()
        if jobid not in self.jobs.keys():
            self.jobs[jobid] = JobControl(jobid)
        jc = self.jobs[jobid]
        self.jobs_lock.release()
        return jc

    def has_jobcontrol(self, jobid):
        """Test wheter the node agent has jobcontrol object given the jobid."""
        has = False
        self.jobs_lock.acquire()
        if jobid in self.jobs.keys():
            has = True
        self.jobs_lock.release()
        return has

    def print_summary(self):
        """Print out the summary information on the screen"""
        if self.agents:
            boss = self.who_is_boss()
            idlest = self.get_idle_nodes()[0]
            print("active:%i,\tboss:(%s, %i),\tidlest:(%s, %.2f)" %
                  (len(self.agents), self.agents[boss][0], boss,
                   idlest[1], idlest[0]))
        pass

    def probe(self):
        """Send out heartbeat, node states; do the regular maintenance work."""
        t0 = time.time()
        while True:
            try:
                t1 = time.time()
                t = max(int(t1 - t0), 1)
                msg = {'op':'live', 'agid':self.id,
                       'args':self.stat.get_metric()}
                self.broadcast(msg)
                if t % 10 == 0:
                    if len(self.agents) < 2:
                        self.start_possible_agents()
                    for agid, agtp in self.agents.items():
                        agip, agtm, _ = agtp
                        if t1 - agtm > 60:
                            self.agents.pop(agid)
                            if self.id == max(self.agents.keys()):
                                self.start_agent(agip)
                if t % 3600 == 0 and self.id == max(self.agents.keys()):
                    self.start_possible_agents()
                self.print_summary()

                # Liang: new feature test
                if self.id == self.who_is_boss():
                    if self.jmgmt is None:
                        self.jmgmt = JobMgmt()
                    else:
                        self.jmgmt.update_stat()
                else:
                    self.jmgmt = None
                time.sleep(1)
            except Exception, err:
                print "Exception:Agent.probe():", err
        pass

    def process_ctvr(self, msg):
        """Process the request for creating a router"""
        jobid = msg['jobid']
        args = msg['args']
        jc = self.get_jobcontrol(jobid)
        jc.create_router(args)
        pass

    def process_job_gather(self, ifn):
        """Process a job config file, allocate the tasks."""
        print "proccess job", ifn
        VRNUM = 80
        jobid = random.randint(0,65535)
        config = ConfigReader(ifn)
        l = self.get_idle_nodes()
        m = 0
        # Liang: allocation strategy is here, needs improvement
        for vrid, vrd in config.vrdetail.items():
            m += 1
            n = min(int(m/VRNUM), len(l)-1)
            # Inform a node to intialize a job
            if (m-1) % VRNUM == 0:
                msg = "jobc%i|%s" % (jobid, config.vrset2msg(config.vrouters))
                self.reliable_send(msg, (l[n][1], BPORT))
            msg = "ctvr%i|%s" % (jobid, config.vrd2msg(vrd))
            self.reliable_send(msg, (l[n][1], BPORT))
            if config.has_upperapp(vrid):
                msg = "ctap%i|%s" % (jobid, config.apd2msg(config.appdetail[vrid]))
                self.reliable_send(msg, (l[n][1], BPORT))
        pass

    def process_job(self, ifn):
        """Process a job config file, allocate the tasks."""
        print "proccess job", ifn
        jobid = random.randint(0,65535)
        config = ConfigReader(ifn)
        m = 0
        l = self.get_idle_nodes()
        # Liang: Debug, use 4 or 5 nodes at most
        l = l[:5]
        self.jmgmt.add_job(jobid, ifn, l)

        for x in l:
            agcpu, agip = x
            # Liang: debug, needs improvement
            #self.agent_in_use.add(agip)

        # Liang: allocation strategy is here, needs improvement
        for x in l:
            msg = {'op':'jobc', 'jobid':jobid, 'args':config.vrouters}
            self.reliable_send(msg, (x[1], BPORT))
        for vrid, vrd in config.vrdetail.items():
            msg = {'op':'ctvr', 'jobid':jobid, 'args':vrd}
            self.reliable_send(msg, (l[m % (len(l))][1], BPORT))
            m += 1
        pass

    def process_jobc(self, msg):
        """Set the router set in corresponding JobControl object"""
        jobid = msg['jobid']
        vrset = msg['args']
        jc = self.get_jobcontrol(jobid)
        jc.set_vrdict(vrset)
        jc.state = 'INIT'
        pass

    def process_jobq(self, msg): 
        """Process the queries for JobControl"""
        jobid = msg['jobid']
        if self.has_jobcontrol(jobid):
            jc = self.get_jobcontrol(jobid)
            replies = jc.reply_vrdict_query(msg['args'])
            msgr = {'op':'jobr', 'jobid':jobid, 'args':replies}
            self.broadcast(msgr)
        pass

    def process_jobr(self, msg):
        """Process the replies for the jobq message."""
        jobid = msg['jobid']
        if self.has_jobcontrol(jobid):
            jc = self.get_jobcontrol(jobid)
            jc.update_vrdict(msg['args'])
        pass

    def process_jobk(self, msg):
        """Terminate a job"""
        jobid = msg['jobid']
        if self.has_jobcontrol(jobid):
            self.jobs_lock.acquire()
            jc = self.jobs.pop(jobid)
            self.jobs_lock.release()
            jc.terminate()
        if self.jmgmt is not None:
            self.jmgmt.delete_job(jobid)
        pass

    def process_tkmv(self, args):
        """Process the replies for the jobq message."""
        pass

    def process_vrdu(self, args):
        """Process vrdict update message"""
        args = args.split('|')
        jobid = int(args[0])
        vrid = int(args[1])
        ip = args[2]
        iport = int(args[3])
        jc = self.get_jobcontrol(jobid)
        jc.update_vrdict(args[1:])
        jc.update_l2p(vrid,ip,iport)
        pass

    def process_message(self, addr, msg):
        """Handle various messages here."""
        try:
            cmd = msg['op']
            args = msg['args'] if msg.has_key('args') else None
            if cmd == "helo":
                pass
            elif cmd == "live":
                self.agents[msg['agid']] = (addr[0], time.time(), args)
                if self.id == msg['agid'] and self.ip != addr[0]:
                    old_id = self.id
                    self.id = random.randint(0, 65535)
                    self.broadcast({'op':'dele', 'args':old_id})
            elif cmd == "ctvr":
                self.process_ctvr(msg)
            elif cmd == "dele":
                self.agents.pop(args)
            elif cmd == "exit":
                self.exit_event.set()
            elif cmd == "job_":
                # Liang: debug here !!!
                if self.id == self.who_is_boss():
                    self.process_job(args)
            elif cmd == "jobc":
                self.process_jobc(msg)
            elif cmd == "jobq":
                self.process_jobq(msg)
            elif cmd == "jobr":
                self.process_jobr(msg)
            elif cmd == "jobk":
                self.process_jobk(msg)
            elif cmd == "tkmv":
                self.process_tkmv(args)
            elif cmd == "vrdu":
                self.process_vrdu(args)
            # Liang: debug purpose
            elif cmd == "ryan":
                print "here:", args
                self.broadcast(args)
        except Exception, err:
            print "Exception:Agent.process_message():", err, msg
        pass

    def reliable_send(self, msg, addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        tid = random.randint(0, 65535)
        msg['tid'] = tid
        msg = dump_msg(msg)
        while True:
            try:
                sock.sendto(msg, addr)
                msg = load_msg(sock.recv(PACKAGE_LEN))
                if msg['op'] == 'ack' and msg['tid'] == tid:
                    break
            except Exception, err:
                print "Exception:Agent.reliable_send():", err
        sock.close()
        pass

    def start(self):
        """Main listening loop of the service"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", BPORT))
        while not self.exit_event.is_set():
            try:
                msg, addr = sock.recvfrom(PACKAGE_LEN)
                msg = load_msg(msg.strip())
                sock.sendto(dump_msg({'op':'ack', 'tid':msg['tid']}), addr)
                t = threading.Thread(target=self.process_message, args=(addr,msg))
                t.daemon = True
                t.start()
            except KeyboardInterrupt:
                break
            except Exception, err:
                print "Exception:Agent.start():", err
        pass

    def start_possible_agents(self):
        all_agents = self.get_all_possible_agents(self.ip)
        active_agents = set()
        for k, v in self.agents.items():
            ip, ts, _ = v
            active_agents.add(ip)            
        for agent in all_agents:
            if agent != self.ip and agent not in active_agents:
                t = threading.Thread(target=self.start_agent, args=(agent,))
                t.daemon = True
                t.start()
        pass

    def get_all_possible_agents(self, ip):
        """Return the IP addresses for all possible agents."""
        agents = []
        nodes_fn = "%s/nodes.txt" % self.get_config_dir()
        if os.path.exists(nodes_fn):
            fh = open(nodes_fn, 'r')
            for line in fh.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                agents.append(line)
        else:
            parts = ip.split('.')
            prefix = "%s.%s.%s." % (parts[0],parts[1],parts[2])
            for i in range(1, 255):
                agent_ip = prefix + str(i)
                agents.append(agent_ip)
        return agents

    def start_agent(self, ip):
        """Start the agent on a node based on given ip."""
        ret = subprocess.call("ssh -o BatchMode=yes -o StrictHostKeyChecking=no %s 'screen -dmS litelab %s; exit'" %
                              (ip,self.get_app_path()),
                              shell=True,
                              stdout=open('/dev/null', 'w'),
                              stderr=subprocess.STDOUT)
        return ret

    def who_is_boss(self):
        """Return boss's id"""
        boss = None
        if self.agents:
            boss = max(self.agents.keys())
        return boss

    pass


def is_running(fn):
    """If there is another monitor running, then quit."""
    # Liang: This function still needs to be fixed. Now, full path must be used.
    uid = os.getuid()
    p = subprocess.Popen(['lsof', '-i', "UDP:%i" % BPORT],
                         stdout = subprocess.PIPE)
    s = p.communicate()[0].strip()
    b = len(s) > 0
    return b

if __name__=="__main__":
    if not is_running(__file__):
        myAgent = Agent()
        try:
            myAgent.start()
        except Exception, err:
            print "NodeAgent:Exception:", err

        # Liang: debug, kill them all, :)
        subprocess.call('pkill -9 -f python', shell=True)
        print myAgent.ip, "exits."
    else:
        print "NodeAgent is already running! Exit..."

    sys.exit(0)
