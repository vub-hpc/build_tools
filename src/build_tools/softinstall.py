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

from easybuild.framework.easyconfig.easyconfig import get_toolchain_hierarchy
from easybuild.framework.easyconfig.parser import EasyConfigParser
from easybuild.framework.easyconfig.tools import det_easyconfig_paths
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.options import set_up_configuration
from vsc.utils import fancylogger
from vsc.utils.run import RunNoShell, RunLoopStdout

from build_tools.filetools import write_tempfile
from build_tools.jobtemplate import BuildJob

SUPPORTED_TCS = ['foss', 'intel', 'gomkl', 'gimkl', 'gimpi']
SUPPORTED_TCGENS = ['2022a', '2023a']

SUPPORTED_FULL_TCS = {}
EB_CFG = None

logger = fancylogger.getLogger()


def set_toolchain_generation(easyconfig, tc_gen=None):
    """
    Determine toolchain generation from easyconfig
    if specified tc_gen is unsupported: return False
    if unsupported generation: return False
    if unsupported toolchain: return False
    if system toolchain: use latest generation
    if unable to determine: return False

    :param easyconfig (string): filename of the target easyconfig
    :param tc_gen (string): toolchain generation (e.g. '2024a')
    """
    if tc_gen:
        if tc_gen in SUPPORTED_TCGENS:
            return tc_gen

        logger.error("Specified toolchain generation %s is not supported. Choose one of %s.",
                     tc_gen, SUPPORTED_TCGENS)
        return False

    global EB_CFG
    if not EB_CFG:
        EB_CFG = set_up_configuration(silent=True)

    ec_path = det_easyconfig_paths([easyconfig])[0]
    parser = EasyConfigParser(ec_path)
    config_dict = parser.get_config_dict()
    toolchain = config_dict['toolchain']
    name = config_dict['name']
    version = config_dict['version']
    name_version = {'name': name, 'version': version}
    logger.debug('toolchain=%s, name,version=%s', toolchain, name_version)

    global SUPPORTED_FULL_TCS
    if not SUPPORTED_FULL_TCS:
        for toolcgen in SUPPORTED_TCGENS:
            SUPPORTED_FULL_TCS[toolcgen] = []
            for toolc in SUPPORTED_TCS:
                try:
                    SUPPORTED_FULL_TCS[toolcgen].extend(get_toolchain_hierarchy({'name': toolc, 'version': toolcgen}))
                except EasyBuildError:
                    # skip if no easyconfig found (Could not find easyconfig for %s toolchain version %s)
                    pass

    # (software with) supported (sub)toolchain and version
    for toolcgen in SUPPORTED_TCGENS:
        if toolchain in SUPPORTED_FULL_TCS[toolcgen] or name_version in SUPPORTED_FULL_TCS[toolcgen]:
            logger.info("Determined toolchain generation %s for %s", toolcgen, easyconfig)
            return toolcgen

    # (software with) supported (sub)toolchain but unsupported version
    for toolcgen in SUPPORTED_TCGENS:
        tcnames = [x['name'] for x in SUPPORTED_FULL_TCS[toolcgen]]
        if toolchain['name'] in tcnames or name in tcnames:
            logger.error("Determined toolchain generation %s for %s is not supported. Choose one of %s.",
                         tc_gen, easyconfig, SUPPORTED_TCGENS)
            return False

    # unsupported toolchains
    # all toolchains have system toolchain, so we need to handle them separately
    # all toolchains have Toolchain easyblock, so checking the easyblock is sufficient
    if config_dict.get('easyblock', '') == 'Toolchain':
        logger.error("Unsupported toolchain %s for %s", name, easyconfig)
        return False

    # software with system toolchain: install in latest generation
    if toolchain['name'] == 'system':
        return sorted(SUPPORTED_TCGENS)[-1]

    logger.error("Unsupported toolchain for %s", easyconfig)
    return False


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
