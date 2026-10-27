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
Functions related to running the Lmod cache

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import sys

from build_tools import stdlib_logger
from build_tools.clusters import APPS, ARCHS, MACHINE, PARTITIONS
from build_tools.filetools import write_tempfile
from build_tools.softinstall import submit_job_script

logger = stdlib_logger(__name__)

LMOD_CACHE_JOB_TEMPLATE = """#!/bin/bash
#SBATCH --time=1:0:0
#SBATCH --output=%x_%j.log
#SBATCH --job-name=lmod_cache_{archdir}
#SBATCH --dependency={dependency}
#SBATCH --partition={partition}
#SBATCH --nodes=1
#SBATCH --ntasks={tasks}
{gpus}{cache_cmd}
"""


def make_cmd_lmod_cache(archdir):
    """
    Generate the command to refresh the Lmod cache of an architecture

    :param archdir: the architecture to create the cache for
    """
    arch = ARCHS[MACHINE][archdir]

    run_lmod_cache = '/usr/libexec/lmod/run_lmod_cache.py'
    common_opts = [
        f'--architecture {archdir}',
        f'--module-basedir {APPS}/{MACHINE}/${{VSC_OS_LOCAL:?}}',
    ]

    # always create the Lmod cache, then create the Open OnDemand module indexes
    cache_calls = [' '.join([run_lmod_cache, '--create-cache'] + common_opts)]

    if arch['ondemand_mod_index'] == '1':
        # generate extra module index for ondemand on selected archs
        # the module index is named after the machine running the selected arch
        spider_opts = ['--create-spider-cache', f'--site-name {MACHINE}']

        cache_calls.append(' '.join([run_lmod_cache] + common_opts + spider_opts))

    # chain the calls so each module index is only created when the
    # previous call succeeded
    lmod_cache_cmd = ' && '.join(cache_calls)
    logger.debug("Lmod cache command: %s", lmod_cache_cmd)

    return lmod_cache_cmd


def submit_lmod_cache_job(partition, jobid=None, **kwargs):
    """
    Run Lmod cache in a Slurm job
    :param partition: the partition to submit the job to
    :param jobid: Slurm jobid the job waits for with an afterok dependency, or None
    """

    cluster = PARTITIONS[partition]['cluster']
    archdir = PARTITIONS[partition]['arch']

    # partitions with gpu_required need a GPU device and the partition's
    # number of tasks for all their jobs
    gpu_required = PARTITIONS[partition]['gpu_required']
    gpus_sbatch = f"#SBATCH {PARTITIONS[partition]['gpus']}\n" if gpu_required else ''
    tasks = PARTITIONS[partition]['tasks'] if gpu_required else 1

    # singleton avoids concurrent cache creations;
    # when a jobid is given, also wait for it to complete successfully
    dependency = 'singleton'
    if jobid is not None:
        dependency += f',afterok:{jobid}'

    cache_job = LMOD_CACHE_JOB_TEMPLATE.format(
        dependency=dependency,
        partition=partition,
        tasks=tasks,
        gpus=gpus_sbatch,
        cache_cmd=make_cmd_lmod_cache(archdir),
        archdir=archdir,
    )

    job_file = write_tempfile(cache_job)

    logger.info("Refreshing Lmod cache on partition %s for architecture %s", partition, archdir)
    ec, out = submit_job_script(job_file, cluster=cluster, **kwargs)

    if ec != 0:
        logger.error("Failed to submit Lmod cache job: %s", out)
        sys.exit(1)

    return ec, out
