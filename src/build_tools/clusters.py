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

# job options
SINGLENODE = 1
THREEHOURS = '03:00:00'
HALFDAY = '11:59:59'

SMALL_JOB = {
    'tasks': 2,
    'walltime': THREEHOURS,
}

# determine running machine
VSC_INSTITUTE_CLUSTER = os.getenv('VSC_INSTITUTE_CLUSTER')
if not VSC_INSTITUTE_CLUSTER:
    logger.error("VSC_INSTITUTE_CLUSTER environment variable is undefined")
    sys.exit(1)

MACHINE = BRUSSEL
if VSC_INSTITUTE_CLUSTER == SOFIA:
    MACHINE = SOFIA

# CPU architecture name including suffix with network fabric
# default: software will be installed by default using this partition
# partition: dict with default CPU and GPU partitions for this arch
# cuda_cc: all CUDA compute capabilities that must be supported on this arch
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
# walltime: walltime for build jobs on this partition
# nodes: default number of nodes for build jobs on this partition
# tasks: default number of tasks for build jobs on this partition
# gpus: Slurm GPU options for build jobs on this partition (empty for CPU partitions)
# gpu_required: the partition requires a GPU device for all jobs on it
PARTITIONS = {
    'ada_gpu': {
        'cluster': ANANSI,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gres=shard:1',
        'gpu_required': False,
    },
    'ampere_gpu': {
        'cluster': HYDRA,
        'arch': 'zen2-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
        'gpu_required': False,
    },
    'hopper_gpu': {
        'cluster': HYDRA,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
        'gpu_required': False,
    },
    'pascal_gpu': {
        'cluster': HYDRA,
        'arch': 'broadwell',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '--gpus-per-node=1',
        'gpu_required': False,
    },
    'zen3': {
        'cluster': MANTICORE,
        'arch': 'zen3',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
        'gpu_required': False,
    },
    'zen3_mpi': {
        'cluster': MANTICORE,
        'arch': 'zen3-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
        'gpu_required': False,
    },
    'zen4': {
        'cluster': HYDRA,
        'arch': 'zen4',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
        'gpu_required': False,
    },
    'zen5_mpi': {
        'cluster': HYDRA,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 4,
        'gpus': '',
        'gpu_required': False,
    },
    # zen4_h200 requires at least 1 GPU and 24 cores per GPU
    'zen4_h200': {
        'cluster': SOFIA,
        'arch': 'zen4-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 24,
        'gpus': '--gpus-per-node=1',
        'gpu_required': True,
    },
    'zen5_dense': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
        'gpu_required': False,
    },
    'zen5_himem': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
        'gpu_required': False,
    },
    'zen5_vis': {
        'cluster': SOFIA,
        'arch': 'zen5-ib',
        'walltime': HALFDAY,
        'nodes': SINGLENODE,
        'tasks': 8,
        'gpus': '',
        'gpu_required': False,
    },
}
