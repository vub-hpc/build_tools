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
Cluster parameters for build submission script

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""
import os
import sys

from build_tools import stdlib_logger

logger = stdlib_logger(__name__)

ANANSI = 'anansi'
APPS = '/apps'
BRUSSEL = 'brussel'
GENT = 'gent'
HYDRA = 'hydra'
MANTICORE = 'manticore'
SOFIA = 'sofia'
SOURCES = 'sources'

# default job options
SINGLENODE = 1
THREEHOURS = '03:00:00'
HALFDAY = '11:59:59'
DEFAULT_WALLTIME = THREEHOURS

VSC_INSTITUTE_CLUSTER = os.getenv('VSC_INSTITUTE_CLUSTER')
if not VSC_INSTITUTE_CLUSTER:
    logger.error("VSC_INSTITUTE_CLUSTER environment variable is undefined")
    sys.exit(1)

if VSC_INSTITUTE_CLUSTER == SOFIA:
    MACHINE = SOFIA
else:
    MACHINE = BRUSSEL

# CPU architecture name including suffix with network fabric
# default: software will be installed by default using this partition
# partition: dict with default CPU and GPU partitions for this arch
# cuda_cc: supported CUDA compute capabilities in the GPU partition
# lmod_json_spider_cache: also create the Lmod spider cache for this arch (default: 0)
ARCHS = {
    BRUSSEL: {
        'broadwell': {
            'default': True,
            'partition': {
                'cpu': 'pascal_gpu',
                'gpu': 'pascal_gpu',
            },
            'cuda_cc': ['6.0', '6.1'],  # Tesla P100, GeForce 1080Ti
        },
        'zen2-ib': {
            'default': True,
            'partition': {
                'cpu': 'ampere_gpu',  # no non-gpu partition available yet
                'gpu': 'ampere_gpu',
            },
            'cuda_cc': ['8.0'],  # A100
        },
        'zen3': {
            'default': False,
            'partition': {
                'cpu': 'zen3',
                'gpu': None,
            },
        },
        'zen3-ib': {
            'default': False,
            'partition': {
                'cpu': 'zen3_mpi',
                'gpu': None,
            },
        },
        'zen4': {
            'default': True,
            'partition': {
                'cpu': 'zen4',
                'gpu': None,
            },
        },
        'zen5-ib': {
            'default': True,
            'partition': {
                'cpu': 'zen5_mpi',
                'gpu': 'ada_gpu',
            },
            'cuda_cc': ['8.9', '9.0'],  # L40S, H200
            'lmod_json_spider_cache': "1",
        },
    }, SOFIA: {
        'zen5-ib': {
            'default': True,
            'partition': {
                'cpu': 'zen5_vis',
                'gpu': 'zen5_vis',
            },
            'cuda_cc': ['8.9'],
        },
        'zen4-ib': {
            'default': True,
            'partition': {
                'cpu': 'zen4_h200',
                'gpu': 'zen4_h200',
            },
            'cuda_cc': ['9.0'],
        },
    },
}

# The key name should match the partition name in Slurm
# cluster: name of the cluster
# arch: architecture of the partition
# long_walltime: walltime for build jobs submitted with --long-job on this partition
# nodes: default number of nodes for build jobs on this partition
# tasks: default number of tasks for build jobs on this partition
# gpus: Slurm GPU options for build jobs on this partition (empty for CPU partitions)

PARTITIONS = {
    'ada_gpu': {
        'cluster': ANANSI,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gres=shard:1',
    },
    'ampere_gpu': {
        'cluster': HYDRA,
        'arch': 'zen2-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
    },
    'hopper_gpu': {
        'cluster': HYDRA,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
    },
    'pascal_gpu': {
        'cluster': HYDRA,
        'arch': 'broadwell',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
    },
    'zen3': {
        'cluster': MANTICORE,
        'arch': 'zen3',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
    },
    'zen3_mpi': {
        'cluster': MANTICORE,
        'arch': 'zen3-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
    },
    'zen4': {
        'cluster': HYDRA,
        'arch': 'zen4',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
    },
    'zen5_mpi': {
        'cluster': HYDRA,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
    },
    # zen4_h200 requires at least 1 GPU and 24 cores per GPU
    'zen4_h200': {
        'cluster': SOFIA,
        'arch': 'zen4-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 24,
        'gpus': '--gpus-per-node=1',
    },
    'zen5_dense': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
    },
    'zen5_himem': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
    },
    'zen5_vis': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'long_walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
    },
}
