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

# CPU architecture name including suffix with network fabric
# default: software will be installed by default using this partitions
# opt: optimization level of each architecture for cross-compilation
# eb: extra options for EasyBuild in this architecture
# partition: dict with default CPU and GPU partitions for this arch
# cuda_cc: suported CUDA compute capabilities in the GPU partition

ARCHS = {
    'broadwell': {
        'default': True,
        'opt': 'mavx2',
        'partition': {
            'cpu': 'pascal_gpu',
            'gpu': 'pascal_gpu',
        },
        'cuda_cc': ['6.0', '6.1'],  # Tesla P100, GeForce 1080Ti
    },
    'haswell-ib': {
        'default': False,
        'opt': 'mavx2',
        'partition': {
            'cpu': 'haswell_mpi',
            'gpu': None,
        },
    },
    'skylake': {
        'default': True,
        'opt': 'mavx512',
        'partition': {
            'cpu': 'skylake',
            'gpu': None,
        },
    },
    'skylake-ib': {
        'default': True,
        'opt': 'mavx512',
        'partition': {
            'cpu': 'skylake_mpi',
            'gpu': None,
        },
    },
    'zen2-ib': {
        'default': True,
        'opt': 'Intel:march=core-avx2;GCC:mavx2',
        'partition': {
            'cpu': 'ampere_gpu',  # no non-gpu partition available yet
            'gpu': 'ampere_gpu',
        },
        'cuda_cc': ['8.0'],  # A100
    },
    'zen3': {
        'default': False,
        'opt': 'Intel:march=core-avx2;GCC:mavx2',
        'partition': {
            'cpu': 'zen3',
            'gpu': None,
        },
    },
    'zen3-ib': {
        'default': False,
        'opt': 'Intel:march=core-avx2;GCC:mavx2',
        'partition': {
            'cpu': 'zen3_mpi',
            'gpu': None,
        },
    },
    'zen4': {
        'default': True,
        'opt': 'Intel:march=rocketlake;GCC:znver4',
        'partition': {
            'cpu': 'zen4',
            'gpu': None,
        },
    },
}

# The key name should match the partition name in Slurm
# cluster: name of the cluster

PARTITIONS = {
    'ampere_gpu': {
        'cluster': 'hydra',
        'arch': 'zen2-ib',
    },
    'haswell_mpi': {
        'cluster': 'chimera',
        'arch': 'haswell-ib',
    },
    'pascal_gpu': {
        'cluster': 'hydra',
        'arch': 'broadwell',
    },
    'skylake': {
        'cluster': 'hydra',
        'arch': 'skylake',
    },
    'skylake_mpi': {
        'cluster': 'hydra',
        'arch': 'skylake-ib',
    },
    'zen3': {
        'cluster': 'manticore',
        'arch': 'zen3',
    },
    'zen3_mpi': {
        'cluster': 'manticore',
        'arch': 'zen3-ib',
    },
    'zen4': {
        'cluster': 'hydra',
        'arch': 'zen4',
    },
}
