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
Unit tests configuration file

@author: Alex Domingo (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os
import sys

import pytest

os.environ["VSC_INSTITUTE_CLUSTER"] = "hydra"

# test the source tree of this repository, even if a different build_tools is installed
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def inputdir(rootdir):
    return os.path.join(rootdir, 'input')
