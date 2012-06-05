#!/usr/bin/env python
# 
# This script solves LP for mapping problem
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2012.02.27 created
#

import os
import sys
import math
import time
import random

# Import PuLP modeler functions
from pulp import *


class Mapping(object):
    """The LP solver for SRouter mapping problem."""
    def __init__(self, states, srouters):
        self.original_states = states
        self.states = states
        self.srouters = srouters
        pass

    def heuristic(self):
        """Sovle the LP problem with heuristic resizing."""
        percent = 1.1
        while True:
            self.heuristic_resize(percent)
            self.solve()
            if 'optimal' in LpStatus[self.prob.status].lower():
                break
            else:
                percent *= 2
        pass

    def solve(self):
        self.prob = LpProblem("The Mapping LP Problem", LpMaximize)
        self.D_vars = LpVariable.dicts("D", self.gen_vars(), 0, 1, LpInteger)
        self.prob += lpSum(self.get_objective()), "Total deployment prefs"
        self.set_physical_constraints()
        self.set_natural_constraints()

        print 'Start solving LP mapping problem ...'
        t0 = time.time()
        self.prob.solve(COIN())
        #self.prob.solve(GLPK())
        print "Status:", LpStatus[self.prob.status]
        print 'Time overheads: %.2f s' % (time.time() - t0)
        pass

    def gen_vars(self):
        """Generate LP variables"""
        lp_vars = []
        for n in self.states:
            for sr in self.srouters:
                D_i_j = '%i_%i' % (n['id'], sr['vrid'])
                lp_vars.append(D_i_j)
        return lp_vars

    def get_objective(self):
        """Objective function"""
        objective = []
        for n in self.states:
            for sr in self.srouters:
                pref = n['pref']
                D_i_j = '%i_%i' % (n['id'], sr['vrid'])
                objective.append(self.D_vars[D_i_j] * pref)
        return objective

    def heuristic_resize(self, percent=1.0):
        """Use heuristic algorithm to reduce the matrix size"""
        trimed = []
        t_cpu = 0
        t_mem = 0
        t_ubd = 0
        t_dbd = 0
        c_cpu = 0
        c_mem = 0
        c_ubd = 0
        c_dbd = 0

        # Calcute SRouters' total needs
        for sr in self.srouters:
            t_cpu += sr['cpu']
            t_mem += sr['mem']
            t_ubd += sr['ubandwidth']
            t_dbd += sr['dbandwidth']

        # Get minimun node set satisfying the needs
        s_states = sorted(self.original_states, key=lambda k: k['pref'], reverse=True)
        for n in s_states:
            trimed.append(n)
            c_cpu += n['cpu']
            c_mem += n['mem']
            c_ubd += n['ubandwidth']
            c_dbd += n['dbandwidth']
            if ( c_cpu >= t_cpu and c_mem >= t_mem and
                 c_ubd >= t_ubd and c_dbd >= t_dbd ):
                break

        # back-off strategy, give extra node than needed.
        extra = int(math.ceil(len(trimed) * percent))
        trimed = s_states[:extra]
        self.states = trimed
        print "Trimed node set:", len(trimed)
        pass

    def set_physical_constraints(self):
        """CPU, memory, bandwidth constraints"""
        for n in self.states:
            cpu_constraints = []
            mem_constraints = []
            ubd_constraints = []
            dbd_constraints = []
            for sr in self.srouters:
                D_i_j = '%i_%i' % (n['id'], sr['vrid'])
                cpu_constraints.append(self.D_vars[D_i_j] * sr['cpu'])
                mem_constraints.append(self.D_vars[D_i_j] * sr['mem'])
                ubd_constraints.append(self.D_vars[D_i_j] * sr['ubandwidth'])
                dbd_constraints.append(self.D_vars[D_i_j] * sr['dbandwidth'])
            self.prob += lpSum(cpu_constraints) <= n['cpu'], ("Node %i CPU constraints" % n['id'])
            self.prob += lpSum(mem_constraints) <= n['mem'], ("Node %i Memory constraints" % n['id'])
            self.prob += lpSum(ubd_constraints) <= n['ubandwidth'], ("Node %i ubandwidth constraints" % n['id'])
            self.prob += lpSum(dbd_constraints) <= n['dbandwidth'], ("Node %i dbandwidth constraints" % n['id'])

        pass

    def set_natural_constraints(self):
        """Each srouter can only be on one node, total num is fixed."""
        total_constraint = []
        for sr in self.srouters:
            column_constraint = []
            for n in self.states:
                D_i_j = '%i_%i' % (n['id'], sr['vrid'])
                column_constraint.append(self.D_vars[D_i_j])
                total_constraint.append(self.D_vars[D_i_j])
            self.prob += lpSum(column_constraint) == 1.0, ("Column %i constraint" % sr['vrid'])

        self.prob += lpSum(total_constraint) == len(self.srouters), ("Total SRouters constraint")
        pass

    def output_result(self):
        """Output deployment Mat"""
        matrix = {}
        print "Status:", LpStatus[self.prob.status]
        for v in self.prob.variables():
            _, i, j = v.name.split('_')
            i = int(i)
            j = int(j)
            if not matrix.has_key(i):
                matrix[i] = {}
            else:
                matrix[i][j] = int(v.varValue)
            #print("%s = %.17f\n" % (v.name, v.varValue))
        return matrix


def gen_node_states(c=100):
    """Test: generate random node states"""
    states = []
    for i in range(c):
        state = {}
        state['id'] = i
        state['pref'] = 1/random.random()
        state['cpu'] = random.randint(90, 100)
        state['mem'] = 32 * 2**20  # KiB
        state['ubandwidth'] = 512 * 2**10  # KiB
        state['dbandwidth'] = 512 * 2**10  # KiB
        states.append(state)
    return states

def gen_srouters(c=100):
    """Test: generate random srouters"""
    srouters = []
    for i in range(c):
        sr = {}
        sr['vrid'] = i
        sr['cpu'] = 1
        sr['mem'] = 50 * 2**10
        sr['ubandwidth'] = 1 * 2**10
        sr['dbandwidth'] = 1 * 2**10
        srouters.append(sr)
    return srouters

if __name__=="__main__":
    states = gen_node_states(256)
    srouters = gen_srouters(400)
    lpsolver = Mapping(states, srouters)
    lpsolver.heuristic()
    #lpsolver.output_result()
    sys.exit(0)
