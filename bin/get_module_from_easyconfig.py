#!/usr/bin/env python3
#
# Copyright 2017-2024 Vrije Universiteit Brussel
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
Helper script to extract the full module name from an easyconfig

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import sys

from easybuild.framework.easyconfig.tools import det_easyconfig_paths, parse_easyconfigs
from easybuild.tools.options import set_up_configuration


easyconfig = sys.argv[1]

set_up_configuration(silent=True)

ec_path = det_easyconfig_paths([easyconfig])[0]

easyconfigs, generated_ecs = parse_easyconfigs([(ec_path, False)])
module = easyconfigs[0]['full_mod_name']
modname, modversion = module.split('/')
print('modname', modname)
print('modversion', modversion)
