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
Parameters for installing IB/non-IB modules

@author: Alex Domingo (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
"""

# software with IB and non-IB modules
# easyblock: real easyblock
# easyblock-ec: easyblock as obtained from the easyconfig
# options: tuple of (name of easyconfig parameter, options to enable IB, options to disable IB)
IB_MODULE_SOFTWARE = {
    'UCX': {
        'easyblock': 'ConfigureMake',
        'easyblock-ec': 'ConfigureMake',
        'options': ('configopts', '--with-verbs', '--without-verbs --without-rdmacm'),
    },
    'UCX-CUDA': {
        'easyblock': 'ConfigureMake',
        'easyblock-ec': 'ConfigureMake',
        'options': ('configopts', '--with-verbs', '--without-verbs --without-rdmacm'),
    },
    'libfabric': {
        'easyblock': 'ConfigureMake',
        'easyblock-ec': 'ConfigureMake',
        'options': ('configopts', '--enable-verbs=yes', '--enable-verbs=no'),
    },
    'PyTorch': {
        'easyblock': 'EB_PyTorch',
        'easyblock-ec': None,
        'options': ('custom_opts', 'USE_IBVERBS=1', 'USE_IBVERBS=0'),
    }
}

IB_OPT_MARK = ['verbs', 'VERBS', 'rdma']

# version suffix of IB archs and modules
IB_MODULE_SUFFIX = '-ib'
