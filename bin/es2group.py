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
Helper script to get the user group for the easyconfigs of an easystack
Raises an error if not all easyconfigs have the same user group

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import contextlib
import os
import sys

from easybuild.framework.easyconfig.parser import EasyConfigParser
from easybuild.framework.easyconfig.tools import det_easyconfig_paths
from easybuild.framework.easystack import EasyStackParser
from easybuild.tools.options import set_up_configuration

from build_tools.hooks_hydra import get_group

# avoid warning about invalid index
os.environ['EASYBUILD_IGNORE_INDEX'] = '1'

es_path = sys.argv[1]

esp = EasyStackParser()
es_data = esp.parse(es_path).ec_opt_tuples
easyconfigs = [x[0] for x in es_data]

groups = set()

with open(os.devnull, 'w') as devnull:
    # make sure any EB logging output is redirected to /dev/null
    with contextlib.redirect_stdout(devnull):
        set_up_configuration(silent=True)
        for ec in easyconfigs:
            ec_path = det_easyconfig_paths([ec])[0]
            parser = EasyConfigParser(ec_path)
            config = parser.get_config_dict()
            groups.add(get_group(config['name'], config['version']))

if len(groups) != 1:
    raise ValueError(f'more than 1 user group found: {groups}')
print(groups.pop())
