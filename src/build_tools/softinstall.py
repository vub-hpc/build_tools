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
Functions related to the software installation

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import shlex
import subprocess
import sys

from build_tools import stdlib_logger
from build_tools.filetools import write_tempfile
from build_tools.jobtemplate import BuildJob

logger = stdlib_logger(__name__)


def run_no_shell(cmd):
    """
    Run a command without using a shell, return (exit_code, output)
    """
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def run_loop_stdout(cmd):
    """
    Run a command using a shell, writing its output to stdout as it is produced,
    return (exit_code, output)
    """
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out_lines = []
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        out_lines.append(line)
    ec = proc.wait()
    return ec, ''.join(out_lines)


def mk_job_name(easyconfigs, host_arch):
    """
    Return name for job script as {easyconfig names}-{host_arch},
    where {easyconfig names} is a concatenation of the names of all given easyconfigs
    :param easyconfigs: space-separated string with path(s) to easyconfig(s)
    :param host_arch: name of host architecture
    """
    names = []
    for easyconfig in easyconfigs.split():
        name = os.path.basename(easyconfig)
        if name.endswith('.eb'):
            name = name[:-3]
        names.append(name)

    job_name = '-'.join(names)

    if host_arch:
        job_name += '-%s' % host_arch

    return job_name


def submit_job_script(job_file, sub_options='', cluster=None, local_exec=False, dry_run=False):
    """
    Execute sbatch command to submit job script to target cluster
    :param job_file: file name of the job script
    :param sub_options: string with options to pass to Slurm
    :param cluster: name of cluster to run the job
    :param local_exec: execute the job script locally
    :param dry_run: print submit command
    """

    sbatch_args = ['sbatch']
    # switch to corresponding cluster via the Slurm -M option
    if cluster:
        sbatch_args.extend(['-M', cluster])
    sbatch_args.append('--parsable')
    if sub_options:
        sbatch_args.extend(shlex.split(sub_options))
    sbatch_args.append(job_file)
    submit_cmd = " ".join(shlex.quote(arg) for arg in sbatch_args)

    if dry_run:
        log_msg = f"(DRY RUN) Job submission command: {submit_cmd}"
        logger.info(log_msg)
        ec, out = 0, log_msg
    elif local_exec:
        logger.debug("Local execution of job script: %s", job_file)
        ec, out = run_loop_stdout(f"bash {job_file}")
    else:
        logger.debug("Job submission command: %s", submit_cmd)
        proc = subprocess.run(sbatch_args, capture_output=True, text=True)
        ec, out = proc.returncode, proc.stdout + proc.stderr
        logger.debug("Job submission output: %s (%s)", out, ec)

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
