#!/usr/bin/env python3
#
# Copyright 2017-2026 Vrije Universiteit Brussel
# All rights reserved.
#
# This file is part of build_tools (https://github.com/vub-hpc/build_tools),
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
##
"""
Helper script to build dict of valid (sub)toolchain-version combinations per valid generation.
The valid toolchain dictionary is read as json from stdin.

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import json
import os
import sys

from easybuild.framework.easyconfig.easyconfig import get_toolchain_hierarchy
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.options import set_up_configuration


def calc_tc_versions(valid_toolchains):
    os.environ['EASYBUILD_IGNORE_INDEX'] = '1'
    os.environ['EASYBUILD_TERSE'] = '1'

    set_up_configuration()

    tc_versions = {}
    for tcgen, tcgen_spec in valid_toolchains.items():
        tcgen_versions = []
        for tc_name in tcgen_spec['toolchains']:
            try:
                tcgen_versions.extend(get_toolchain_hierarchy({'name': tc_name, 'version': tcgen}))
            except EasyBuildError:
                # skip if no easyconfig found for toolchain-version
                pass
        tc_versions[tcgen] = {
            'toolchains': tcgen_versions,
            'subdir': tcgen_spec['subdir'],
        }
    print(json.dumps(tc_versions))


if __name__ == "__main__":
    valid_toolchains = json.loads(sys.stdin.read())
    calc_tc_versions(valid_toolchains)
