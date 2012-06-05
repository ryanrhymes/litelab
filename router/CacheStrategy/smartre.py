#!/usr/bin/env python
# 
# This script implements SmartRE.
#
# Liang Wang @ Dept. Computer Science, University of Helsinki, Finland
# 2011.12.06 created
#

import os
import sys

from common import *
from cache_fifobucket import CacheFIFOBucket
from messageheader import MessageHeader
from smartreshim import *

class SmartRE(object):
    """Implement SmartRE according to Anand's paper."""

    def __init__(self, router, cachesize):
        self.router = router
        self._cache = None
        self.logfh = None

        # Liang: The manifest should be in the same folder as topology file
        manifest_file = '%s/manifest' % os.path.dirname(router.argsdict['tfile'])
        self.manifest = get_manifest(manifest_file)
        pass

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, val):
        self._cache = val
        self._cache.init_bucket( get_bucket_quota(self.manifest, self.router.vrid) )

    def ihandler(self, data):
        """Equivalent to the ProcessPacketInterior function in the paper."""
        rt_hdr = MessageHeader()
        rt_hdr.recv(data)
        re_hdr = SmartREShim()
        re_hdr.recv(rt_hdr.data)
        rt_hdr.hop += 1
        rt_hdr.hit += 1

        # Log the message
        msg_type = "???"
        if rt_hdr.type == MessageType.REQUEST:
            msg_type = "REQ"
        if rt_hdr.type == MessageType.RESPONSE:
            msg_type = "RSP"
        # Should we reset footprint?
        if re_hdr.matches > 0:
            rt_hdr.hit = 1

        logme2(self.logfh, rt_hdr.seq, rt_hdr.src, rt_hdr.dst, msg_type, re_hdr.matches, rt_hdr.id)

        if rt_hdr.type == MessageType.RESPONSE:
            decoded_data, nullify_data = self.decode(re_hdr)
            hh = hash_header(rt_hdr)
            if self.in_range(re_hdr.pathid, hh):
                self.cache.add_chunk(re_hdr.pathid, self.router.vrid, 
                                     hh, nullify_data)
                pass
            re_hdr.data = decoded_data
            rt_hdr.data = re_hdr.send()

        data = rt_hdr.send()
        return data

    def decode(self, re_hdr):
        """Expand the message based on the information in MatchSpecs"""
        decoded_data = re_hdr.data
        nullify_data = []

        i = 0
        for m in re_hdr.matchspecs:
            nullify_data.append(decoded_data[i:m.position])
            nullify_data.append(chr(0) * (m.region[1] - m.region[0] + 1))
            i = m.position + 1
        nullify_data.append(decoded_data[i:])
        nullify_data = ''.join(nullify_data)

        i = 0
        for j in range(re_hdr.matches):
            m = re_hdr.matchspecs[i]
            index_info = self.cache.get_index_by_hh(m.header_hash)
            if index_info is not None:
                pathid_c, vrid_c, index_c = index_info
                pkg_c = self.cache.get_chunk(pathid_c, vrid_c, index_c)
                decoded_data = (decoded_data[: m.position] + 
                                pkg_c[m.region[0] : m.region[1] + 1] +
                                decoded_data[m.position + 1 :])
                re_hdr.del_matchspec(m)
            else:
                i += 1
            pass

        return decoded_data, nullify_data


    def in_range(self, pathid, header_hash):
        """Check if the header hash falls in the router's range."""
        b_in = False
        # Needs to be synced with manifest design
        rng = self.manifest[pathid][self.router.vrid]['range']
        if rng[0] <= header_hash and header_hash < rng[1]:
            b_in = True
        return b_in

    pass


if __name__ == '__main__':
    sys.exit(0)
