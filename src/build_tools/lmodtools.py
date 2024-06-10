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
Functions related to running the Lmod cache

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import sys

from vsc.utils import fancylogger

from build_tools.clusters import PARTITIONS
from build_tools.filetools import APPS_BRUSSEL, write_tempfile
from build_tools.softinstall import submit_job_script

logger = fancylogger.getLogger()

LMOD_CACHE_LICENSE = 'lmod_cache'
LMOD_CACHE_CLUSTERS = ['hydra', 'manticore']
LMOD_CACHE_JOB_TEMPLATE = """#!/bin/bash
#SBATCH --time=1:0:0
#SBATCH --mem=1g
#SBATCH --output=%x_%j.log
#SBATCH --job-name=lmod_cache_{archdir}
#SBATCH --dependency=singleton{jobids_depend}
#SBATCH --partition={partition}
{cache_cmd}
"""


def submit_lmod_cache_job(partition, jobids_depend=None, cluster=None, **kwargs):
    """
    Run Lmod cache in a Slurm job
    :param partition: the partition to submit the job to
    :param jobids_depend: list of strings: jobids on with to set job dependency
    :param cluster: the Slurm cluster to submit the job to.

    if cluster is None, load the cluster module corresponding to the current partition
    if cluster is False, don’t purge/load a cluster module (use the currently active cluster)
    """

    archdir = PARTITIONS[partition]['arch']
    if cluster is None:
        cluster = PARTITIONS[partition]['cluster']

    cache_cmd = [
        '/usr/libexec/lmod/run_lmod_cache.py',
        '--create-cache',
        f'--architecture {archdir}',
        f'--module-basedir {APPS_BRUSSEL}/$VSC_OS_LOCAL',
    ]

    cache_job = LMOD_CACHE_JOB_TEMPLATE.format(
        jobids_depend=f',afterok:{":".join(jobids_depend)}' if jobids_depend else '',
        partition=partition,
        cache_cmd=' '.join(cache_cmd),
        archdir=archdir,
    )

    job_file = write_tempfile(cache_job)

    logger.info(
        "Refreshing Lmod cache on partition %s for architecture %s", partition or 'default', archdir or 'default')
    ec, out = submit_job_script(job_file, cluster=cluster, **kwargs)

    if ec != 0:
        logger.error("Failed to submit Lmod cache job: %s", out)
        sys.exit(1)

    return ec, out
