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
Helper script to install a dummy module with submit_build.py

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import os
import sys

from easybuild.framework.easyconfig.tools import parse_easyconfigs
from easybuild.tools.filetools import copy_file, mkdir, remove_file, symlink
from easybuild.tools.options import set_up_configuration

from build_tools.filetools import poke

easyconfig = sys.argv[1]
module_path = sys.argv[2]
footer = sys.argv[3]

set_up_configuration()

easyconfigs, generated_ecs = parse_easyconfigs([(easyconfig, False)])
mod_name, mod_version = easyconfigs[0]['full_mod_name'].split('/')
full_mod_path = os.path.join(module_path, 'all', mod_name, mod_version + '.lua')
copy_file(footer, full_mod_path)
poke(full_mod_path)

moduleclass = easyconfigs[0]['ec']['moduleclass']
symlink_dir_path = os.path.join(module_path, moduleclass, mod_name)
mkdir(symlink_dir_path, parents=True)
symlink_mod_path = os.path.join(symlink_dir_path, mod_version + '.lua')
remove_file(symlink_mod_path)
symlink(full_mod_path, symlink_mod_path)
