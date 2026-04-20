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
Cluster parameters for build submission script

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""


ANANSI = 'anansi'
APPS = '/apps'
ARCH = 'arch'
BRUSSEL = 'brussel'
CLUSTER = 'cluster'
CPU = 'cpu'
DEFAULT = 'default'
GENT = 'gent'
GPU = 'gpu'
HYDRA = 'hydra'
MANTICORE = 'manticore'
PARTITION = 'partition'
SOFIA = 'sofia'
SOURCES = 'sources'

# CPU architecture name including suffix with network fabric
# default: software will be installed by default using this partitions
# eb: extra options for EasyBuild in this architecture
# partition: dict with default CPU and GPU partitions for this arch
# cuda_cc: suported CUDA compute capabilities in the GPU partition
ARCHS = {
    BRUSSEL: {
        'broadwell': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'pascal_gpu',
                GPU: 'pascal_gpu',
            },
            'cuda_cc': ['6.0', '6.1'],  # Tesla P100, GeForce 1080Ti
        },
        'haswell-ib': {
            DEFAULT: False,
            PARTITION: {
                CPU: 'haswell_mpi',
                GPU: None,
            },
        },
        'skylake': {
            DEFAULT: False,
            PARTITION: {
                CPU: 'skylake',
                GPU: None,
            },
        },
        'skylake-ib': {
            DEFAULT: False,
            PARTITION: {
                CPU: 'skylake_mpi',
                GPU: None,
            },
        },
        'zen2-ib': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'ampere_gpu',  # no non-gpu partition available yet
                GPU: 'ampere_gpu',
            },
            'cuda_cc': ['8.0'],  # A100
        },
        'zen3': {
            DEFAULT: False,
            PARTITION: {
                CPU: 'zen3',
                GPU: None,
            },
        },
        'zen3-ib': {
            DEFAULT: False,
            PARTITION: {
                CPU: 'zen3_mpi',
                GPU: None,
            },
        },
        'zen4': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'zen4',
                GPU: None,
            },
        },
        'zen5-ib': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'zen5_mpi',
                GPU: 'ada_gpu',
            },
            'cuda_cc': ['8.9', '9.0'],  # L40S, H200
        },
    }, SOFIA: {
        'zen5-ib': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'zen5_vis',
                GPU: 'zen5_vis',
            },
            'cuda_cc': ['8.9'],
        },
        'zen4-ib': {
            DEFAULT: True,
            PARTITION: {
                CPU: 'zen4_h200',
                GPU: 'zen4_h200',
            },
            'cuda_cc': ['9.0'],
        },
    },
}

# The key name should match the partition name in Slurm
# cluster: name of the cluster

PARTITIONS = {
    'ada_gpu': {
        CLUSTER: ANANSI,
        ARCH: 'zen5-ib',
    },
    'ampere_gpu': {
        CLUSTER: HYDRA,
        ARCH: 'zen2-ib',
    },
    'hopper_gpu': {
        CLUSTER: HYDRA,
        ARCH: 'zen5-ib',
    },
    'pascal_gpu': {
        CLUSTER: HYDRA,
        ARCH: 'broadwell',
    },
    'skylake': {
        CLUSTER: HYDRA,
        ARCH: 'skylake',
    },
    'skylake_mpi': {
        CLUSTER: HYDRA,
        ARCH: 'skylake-ib',
    },
    'zen3': {
        CLUSTER: MANTICORE,
        ARCH: 'zen3',
    },
    'zen3_mpi': {
        CLUSTER: MANTICORE,
        ARCH: 'zen3-ib',
    },
    'zen4': {
        CLUSTER: HYDRA,
        ARCH: 'zen4',
    },
    'zen5_mpi': {
        CLUSTER: HYDRA,
        ARCH: 'zen5-ib',
    },
    'zen4_h200': {
        CLUSTER: SOFIA,
        ARCH: 'zen4-ib',
    },
    'zen5_dense': {
        CLUSTER: SOFIA,
        ARCH: 'zen5-ib',
    },
    'zen5_himem': {
        CLUSTER: SOFIA,
        ARCH: 'zen5-ib',
    },
    'zen5_vis': {
        CLUSTER: SOFIA,
        ARCH: 'zen5-ib',
    },
}
