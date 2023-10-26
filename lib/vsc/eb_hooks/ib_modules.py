#
# Copyright 2017-2023 Vrije Universiteit Brussel
#
# This file is part of eb_hooks,
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/vub-hpc/eb_hooks
#
# All rights reserved.
#
"""
Parameters for installing IB/non-IB modules

@author: Alex Domingo (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
"""

# software with IB and non-IB modules
# tuple with name of easyconfig parameter and its options to enable/disable IB
IB_MODULE_SOFTWARE = {
    'UCX': ('configopts', '--with-verbs', '--without-verbs --without-rdmacm'),
    'UCX-CUDA': ('configopts', '--with-verbs', '--without-verbs --without-rdmacm'),
    'libfabric': ('configopts', '--enable-verbs=yes', '--enable-verbs=no'),
    'PyTorch': ('custom_opts', 'USE_IBVERBS=1', 'USE_IBVERBS=0'),
}

IB_OPT_MARK = ['verbs', 'VERBS', 'rdma']

# version suffix of IB archs and modules
IB_MODULE_SUFFIX = '-ib'
