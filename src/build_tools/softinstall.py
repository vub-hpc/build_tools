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
Functions related to the software installation

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import re

from vsc.utils import fancylogger
from vsc.utils.run import RunNoShell, RunLoopStdout

from build_tools.filetools import write_tempfile
from build_tools.jobtemplate import BuildJob

logger = fancylogger.getLogger()

TOOLCHAIN_FORMAT = r"20[1-2][0-9][ab]"

SUBTOOLCHAINS = {
    '2024a': ['GCCcore-13.3.0', 'GCC-13.3.0', 'intel-compilers-2024.2.0'],
    '2025a': ['GCCcore-14.2.0', 'GCC-14.2.0', 'intel-compilers-2025.1.1'],
}


def set_toolchain_generation(easyconfig, user_toolchain=False):
    """
    Determine toolchain generation from easyconfig
    Use user_toolchain if it is a valid toolchain_generation
    :param easyconfig: filename of the target easyconfig
    :param easycinfig: string with toolchain specification
    """
    toolchain_generation = None

    if user_toolchain:
        if re.match('^' + TOOLCHAIN_FORMAT + '$', user_toolchain):
            toolchain_generation = user_toolchain
        else:
            logger.error("Specified toolchain generation is not valid: %s", user_toolchain)
            return False
    else:
        found_tc = re.findall(TOOLCHAIN_FORMAT, easyconfig)
        found_tc = set(found_tc)  # remove duplicates (multiple toolchain labels might present in long paths)
        if len(found_tc) == 1:
            toolchain_generation = found_tc.pop()
        else:
            # Try to determine toolchain generation based on sub-toolchain
            for main_tc, sub_tc in SUBTOOLCHAINS.items():
                if any([re.search(tc, easyconfig) for tc in sub_tc]):
                    toolchain_generation = main_tc
                    break

    logger.debug("Toolchain generation: %s", toolchain_generation)

    return toolchain_generation


def mk_job_name(easyconfig, host_arch, target_arch=None):
    """
    Return name for job script as {easyconfig name}-{host_arch}-{target_arch}
    :param easyconfig: path to easyconfig
    :param host_arch: name of host architecture
    :param host_arch: name of target architecture
    """

    job_name = re.sub('.eb$', '', os.path.basename(easyconfig))

    if host_arch:
        job_name += '-%s' % host_arch

    if target_arch and target_arch != host_arch:
        job_name += '-%s' % target_arch

    return job_name


def submit_job_script(job_file, sub_options='', cluster='hydra', local_exec=False, dry_run=False):
    """
    Execute sbatch command to submit job script to target cluster
    :param job_file: file name of the job script
    :param sub_options: string with options to pass to Slurm
    :param cluster: name of cluster to run the job
    :param local_exec: execute the job script locally
    :param dry_run: print submit command
    """

    submit_cmd = []
    # switch to corresponding cluster and submit
    if cluster:
        submit_cmd.append("module --force purge")
        submit_cmd.append(f"module load cluster/{cluster}")

    submit_cmd.append(f"sbatch --parsable {sub_options} {job_file}")
    submit_cmd = " && ".join(submit_cmd)

    if dry_run:
        log_msg = f"(DRY RUN) Job submission command: {submit_cmd}"
        logger.info(log_msg)
        ec, out = 0, log_msg
    elif local_exec:
        logger.debug("Local execution of job script: %s", job_file)
        ec, out = RunLoopStdout.run(f"bash {job_file}")
    else:
        logger.debug("Job submission command: %s", submit_cmd)
        ec, out = RunNoShell.run(f'bash -c "{submit_cmd}"')

    return ec, out


def submit_build_job(job_options, keep_job=False, **kwargs):
    """
    Generate job script from BUILD_JOB template and submit it with Slurm to target cluster
    :param job_options: dict with options to pass to job template
    :param keep_job: do not delete the job script file
    """

    job_script = BuildJob.substitute(job_options)
    job_file = write_tempfile(job_script)
    logger.debug("Job script written to %s", job_file)

    ec, out = submit_job_script(job_file, **kwargs)

    if not keep_job:
        try:
            os.remove(job_file)
        except IOError as err:
            logger.error("Failed to remove job file '%s': %s", job_file, err)

    return ec, out
