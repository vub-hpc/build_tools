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
Unit tests for build_tools.ib_modules

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import pytest

from build_tools.ib_modules import is_ib_option


@pytest.mark.parametrize('opt', [
    '--with-verbs',
    '--without-verbs',
    '--with-rdmacm',
    '--without-rdmacm',
    '--enable-verbs=yes',
    '--enable-verbs=no',
    'USE_IBVERBS=1',
    'USE_IBVERBS=0',
])
def test_is_ib_option_true(opt):
    assert is_ib_option(opt)


@pytest.mark.parametrize('opt', [
    '--enable-shared',
    '--with-verbosus',
    '--disable-rdma-compat',
    '--with-munge',
])
def test_is_ib_option_false(opt):
    assert not is_ib_option(opt)
