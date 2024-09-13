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

# toolchains having the generation as their version
GEN_TCS = ['gfbf', 'gompi', 'foss', 'iimpi', 'iimkl', 'intel', 'gomkl', 'gimkl', 'gimpi']

# toolchains with custom versions
NON_GEN_TCS = ['GCCcore', 'GCC', 'intel-compilers']

# all toolchains
TCS = GEN_TCS + NON_GEN_TCS

BANNED_TCS = ['fosscuda', 'intelcuda', 'gompic', 'iimpic']

# https://docs.easybuild.io/common-toolchains/#common_toolchains_overview
# allowed toolchain generations and corresponding toolchain-versions
TC_GENS = {
    '2022a': ['GCCcore-11.3.0', 'GCC-11.3.0', 'intel-compilers-2022.1.0'] + [f'{x}-2022a' for x in GEN_TCS],
    '2023a': ['GCCcore-12.3.0', 'GCC-12.3.0', 'intel-compilers-2023.1.0'] + [f'{x}-2023a' for x in GEN_TCS],
    # hold off 2024a until EB-5 branch is merged into develop
    # '2024a': ['GCCcore-13.3.0', 'GCC-13.3.0', 'intel-compilers-2024.2.0'] + [f'{x}-2024a' for x in GEN_TCS],
}


def set_toolchain_generation(easyconfig, tc_gen=None):
    """
    Determine toolchain generation from easyconfig
    Return tc_gen if provided and allowed
    Return False if toolchain or toolchain-version is disallowed

    :param easyconfig (string): filename of the target easyconfig
    :param tc_gen (string): toolchain generation (e.g. '2024a')
    """
    allowed_tcgens = TC_GENS.keys()

    if tc_gen:
        if tc_gen in allowed_tcgens:
            return tc_gen

        logger.error("Specified toolchain generation %s is not allowed. Choose one of %s.",
                     tc_gen, list(allowed_tcgens))
        return False

    # try to determine toolchain generation from matching toolchain-version in TC_GENS
    for main_tc, sub_tc in TC_GENS.items():
        if any(re.search(rf'(-|^){tc}(-|.eb$)', easyconfig) for tc in sub_tc):
            logger.debug("Determined toolchain generation: %s", main_tc)
            return main_tc

    # block known toolchain if toolchain-version is not in TC_GENS
    matches = [re.search(rf'(-|^)({x}-.*?)(-|.eb$)', easyconfig) for x in TCS]
    tc_versions = [x.group(2) for x in matches if x]
    if tc_versions:
        logger.error("Determined toolchain-version is banned: %s", tc_versions)
        return False

    # block banned toolchains
    matches = [re.search(rf'(-|^)({x})-.*?(-|.eb$)', easyconfig) for x in BANNED_TCS]
    tcs = [x.group(2) for x in matches if x]
    if tcs:
        logger.error("Determined toolchain is banned: %s", tcs)
        return False

    # assume SYSTEM toolchain, use latest generation
    tc_gen = sorted(allowed_tcgens)[-1]
    logger.debug("Unable to determine toolchain, assuming SYSTEM toolchain, using %s", tc_gen)
    return tc_gen


def mk_job_name(easyconfig, host_arch, target_arch=None):
    """
    Return name for job script as {easyconfig name}-{host_arch}-{target_arch}
    :param easyconfig: path to easyconfig
    :param host_arch: name of host architecture
    :param host_arch: name of target architecture
    """

    job_name = re.sub('.eb$', '', os.path.basename(easyconfig))

    if host_arch:
        job_name = f'{job_name}-{host_arch}'

    if target_arch and target_arch != host_arch:
        job_name = f'{job_name}-{target_arch}'

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
