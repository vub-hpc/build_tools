#!/usr/bin/env python3
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
Script to submit easyconfig as jobs to all different architectures.

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import argparse
import logging
import os
import re
import sys

from build_tools import hooks_hydra, stdlib_logger
from build_tools.clusters import APPS, ARCHS, BRUSSEL, GENT, MACHINE, PARTITIONS, SMALL_JOB, SOFIA, SOURCES
from build_tools.hooks_hydra import (
    SUBDIR_MODULES_BWRAP,
    SUFFIX_MODULES_PATH,
    SUFFIX_MODULES_SYMLINK,
    VALID_MODULES_SUBDIRS,
)
from build_tools.lmodtools import make_cmd_lmod_cache, submit_lmod_cache_job
from build_tools.package import VERSION
from build_tools.softinstall import mk_job_name, run_no_shell, submit_build_job

logger = stdlib_logger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')


# repositories with easyconfigs
EASYCONFIG_REPOS = [
    # our site repo (https://github.com/vscentrum/vsc-software-stack/tree/site-vub)
    os.path.join("site-vub", "easyconfigs"),
    "easybuild",  # main EasyBuild repo (https://github.com/easybuilders/easybuild-easyconfigs)
]
EASYBLOCK_REPO = os.path.join("site-vub", "easyblocks", "*", "*.py")

SOURCEPATH = {
    BRUSSEL: os.pathsep.join([
        os.path.join(APPS, BRUSSEL, SOURCES),
        os.path.join(APPS, GENT, SOURCES),
    ]),
    SOFIA: os.path.join(APPS, SOFIA, SOURCES),
}

DEFAULT_ARCHS = [arch for (arch, prop) in ARCHS[MACHINE].items() if prop['default']]
LOCAL_ARCH = os.getenv('VSC_ARCH_LOCAL', '') + os.getenv('VSC_ARCH_SUFFIX', '')

# sanity check: all partitions defined in ARCHS must exist in PARTITIONS
for _arch, _props in ARCHS[MACHINE].items():
    for _kind in ('cpu', 'gpu'):
        _part = _props['partition'][_kind]
        if _part and _part not in PARTITIONS:
            logger.error(f"Partition '{_part}' for architecture '{_arch}' is not defined in PARTITIONS")
            sys.exit(1)


def strlist(value):
    """Split a comma-separated string into a list of strings"""
    return value.split(',')


def main():
    """Submit job script to deploy software installation with EasyBuild"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Submit easyconfig as jobs to all different architectures.')
    parser.add_argument('-v', '--version', action='version', version=f"%(prog)s {VERSION}")
    parser.add_argument('-a', '--arch', type=strlist, default=None,
                        help='CPU architecture of the host system and the build')
    parser.add_argument('-b', '--bwrap', action='store_true',
                        help='Reinstall in 2 steps via new namespace with bwrap (no robot)')
    parser.add_argument('-c', '--lang-c', action='store_true',
                        help='Set LANG=C in the build (instead of unicode)')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Set log level to DEBUG (default is INFO)')
    parser.add_argument('-D', '--dry-run', action='store_true',
                        help='Do not fetch/install, set debug log level')
    parser.add_argument('-e', '--extra-eb-flags', default=None,
                        help='Extra flags to pass to EasyBuild')
    parser.add_argument('-f', '--append-mod-footer', default=None,
                        help='Path to extra footer for module file')
    parser.add_argument('-g', '--gpu',
                        choices=['detect', 'detect-nodevice', 'force', 'force-nodevice'], default='detect',
                        help='GPU behaviour: detect (detect GPU software from easyconfig filename, default), '
                             'detect-nodevice (detect and run job without a GPU device), '
                             'force (use GPU partitions on supported archs) or '
                             'force-nodevice (force without a GPU device)')
    parser.add_argument('-k', '--keep', action='store_true',
                        help='Do not delete the job file at the end')
    parser.add_argument('-l', '--local', action='store_true',
                        help='Do not submit as job, run locally')
    parser.add_argument('-m', '--lmod-cache', choices=['after', 'only', 'skip'], default='after',
                        help='Lmod cache behaviour: after (make cache after the installation, default), '
                             'only (just refresh the cache) or skip (install without making the cache)')
    parser.add_argument('-n', '--pre-fetch', action='store_true',
                        help='Pre-fetch sources before submitting build jobs')
    parser.add_argument('-p', '--partition', type=strlist, default=None,
                        help='Slurm partition for the build')
    parser.add_argument('-q', '--extra-job-flags', default='',
                        help='Extra flags to pass to Slurm')
    parser.add_argument('-r', '--append-robot-cwd', action='store_true',
                        help='Append current working dir to robot path')
    parser.add_argument('-s', '--job-small', action='store_true',
                        help=f"Submit jobs with a shorter walltime ({SMALL_JOB['walltime']}) "
                             f"and less tasks ({SMALL_JOB['tasks']})")
    parser.add_argument('-t', '--tmp', choices=['shm', 'tmp', 'scratch'], default='shm',
                        help='Temporary disk for the build: shm (/dev/shm, default), '
                             'tmp (/tmp) or scratch ($VSC_SCRATCH_VO_USER)')
    parser.add_argument('easyconfigs', nargs='*',
                        help='easyconfig file(s) to install')
    opts = parser.parse_args()

    venv = os.getenv('VIRTUAL_ENV')
    if not venv:
        logger.error("VIRTUAL_ENV environment variable is undefined, "
                     "please activate the build_tools virtual environment")
        sys.exit(1)

    vscsoftstack_root = os.path.join(os.path.dirname(venv), 'vsc-software-stack')
    if not os.path.isdir(vscsoftstack_root):
        logger.error(
            f"Cannot locate 'vsc-software-stack' repo in: {vscsoftstack_root} - "
            "Please clone that repo in the parent folder of your virtual environment directory"
        )
        sys.exit(1)

    # Default job options
    job = {
        'appsmnt': '/vscmnt/brussel_pixiu_apps/_apps_brussel',
        'bwrap': '0',
        'extra_mod_footer': None,
        'langcode': 'en_US.utf8',
        'lmod_cache': '1',
        'machine': MACHINE,
        'tmp': '/dev/shm',
        'venv_activate': os.getenv('VSC_VENV_ACTIVATE', '$HOME/EB5/eb5env/bin/activate'),
    }

    # Easybuild default paths
    # start using environment from local machine, job scripts get custom paths
    ebconf = {
        'accept-eula-for': 'Intel-oneAPI,CUDA,cuDNN,NVHPC',
        'buildpath': os.path.join(job['tmp'], 'eb-submit-build-fetch'),
        'hooks': hooks_hydra.__file__,
        'include-easyblocks': os.path.join(vscsoftstack_root, EASYBLOCK_REPO),
        'installpath': os.path.join(APPS, MACHINE, '${VSC_OS_LOCAL:?}', LOCAL_ARCH),
        'prefer-python-search-path': 'EBPYTHONPREFIXES',
        'robot-paths': ":".join([os.path.join(vscsoftstack_root, repo) for repo in EASYCONFIG_REPOS]),
        'sourcepath': SOURCEPATH[MACHINE],
    }

    # EB command line options (same for all build jobs)
    eb_options = [
        '--logtostdout',
        '--module-extensions',
        '--zip-logs=bzip2',
        '--module-depends-on',
        f'--suffix-modules-path={SUFFIX_MODULES_PATH}',
        f'--moduleclasses={",".join(os.path.join(x, SUFFIX_MODULES_SYMLINK) for x in VALID_MODULES_SUBDIRS)}',
    ]

    if opts.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        eb_options.append('--debug')

    dry_run = opts.dry_run
    if dry_run:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info('Doing a dry-run, no fetch/install/lmod-cache')

    # Handle Lmod cache options
    # (early due to potential skip)
    if opts.lmod_cache == 'skip':
        job['lmod_cache'] = '0'
        logger.info("Not running Lmod cache after installation")
    elif opts.lmod_cache == 'only':
        for arch in DEFAULT_ARCHS:
            submit_lmod_cache_job(ARCHS[MACHINE][arch]['partition']['cpu'], dry_run=dry_run)
        sys.exit(0)

    if not opts.easyconfigs:
        logger.error("No easyconfig is given...")
        sys.exit(1)

    # Easyconfig list
    easyconfig = ' '.join(opts.easyconfigs)
    job['easyconfig'] = easyconfig
    logger.info("Preparing to install %s", easyconfig)

    # Host archs: define arch_stack
    local_exec = opts.local
    if local_exec:
        if LOCAL_ARCH not in ARCHS[MACHINE]:
            logger.error("Local system has unsupported architecture: '%s'", LOCAL_ARCH)
            sys.exit(1)
        logger.info("Building on local architecture: %s", LOCAL_ARCH)
        arch_stack = [LOCAL_ARCH]
    elif opts.arch:
        arch_stack = opts.arch
        unknown_archs = [arch for arch in arch_stack if arch not in ARCHS[MACHINE]]
        if unknown_archs:
            logger.error("Unknown archs: %s", ", ".join(unknown_archs))
            sys.exit(1)
    else:
        arch_stack = DEFAULT_ARCHS

    logger.debug("List of architectures: %s", arch_stack)

    # Slurm partitions: define build_hosts
    if opts.partition:
        # given list of partitions overwrites all other options
        unknown_parts = [part for part in opts.partition if part not in PARTITIONS]
        if unknown_parts:
            logger.error("Unknown partitions: %s", ", ".join(unknown_parts))
            sys.exit(1)
        partition_stack = opts.partition
        if opts.arch:
            logger.warning("Overwriting given architectures with the architectures of given partitions")
        arch_stack = [PARTITIONS[part]['arch'] for part in partition_stack]
        build_hosts = list(zip(arch_stack, partition_stack))
    else:
        # initially target default CPU partitions for all selected architectures
        # in case of builds for GPUs, the build host might change down the line if suitable GPU partitions exist
        build_hosts = [(arch, ARCHS[MACHINE][arch]['partition']['cpu']) for arch in arch_stack]

    # remove duplicates and clean-up list of build hosts
    build_hosts = {(arch, part) for (arch, part) in build_hosts if arch and part}

    logger.debug("Initial target build hosts: %s", ', '.join([f'{p} ({a})' for (a, p) in build_hosts]))

    # Switch build language to C
    if opts.lang_c:
        job['langcode'] = 'C'

    # Set robot paths
    if opts.append_robot_cwd:
        ebconf['robot-paths'] += ':' + os.getcwd()
    job['robot_paths'] = ebconf['robot-paths']

    # Add extra footer
    if opts.append_mod_footer:
        if os.path.exists(opts.append_mod_footer):
            job['extra_mod_footer'] = opts.append_mod_footer
        else:
            logger.error("Could not find extra footer: %s", opts.append_mod_footer)
            sys.exit(1)

        eb_options.append(f'--modules-footer={job["extra_mod_footer"]}')

    # Execute pre-fetch
    if opts.pre_fetch:
        # fetch sources before submitting build jobs
        fetch_opts = ['--stop=fetch', '--robot', '--ignore-locks']
        if opts.extra_eb_flags:
            fetch_opts.append(opts.extra_eb_flags)
        for opt, path in ebconf.items():
            # exclude --hooks and empty options from the fetch command
            if opt not in ['hooks'] and path is not None:
                fetch_opts.append(f'--{opt}={path}')
        if dry_run:
            fetch_opts.append('-x')  # extended dry-run

        fetch_cmd = f'eb {" ".join(fetch_opts)} {easyconfig}'

        logger.info("Fetching missing sources for %s and its dependencies...", easyconfig)
        ec, out = run_no_shell(fetch_cmd)

        if dry_run:
            logger.debug(out)
        elif ec == 0:
            out_msg = re.findall('Build succeeded.*', out)
            out_msg = "\n".join(out_msg).replace('Build succeeded', 'Sources are ready')
            logger.info(out_msg)
        else:
            logger.error("Failed to fetch sources for %s: %s", easyconfig, out)
            sys.exit(1)

    # Handle bwrap
    if opts.bwrap:
        job['bwrap'] = 1
        eb_options.extend([
            '--rebuild',
            f'--subdir-modules={SUBDIR_MODULES_BWRAP}',
        ])
    else:
        # robot is not supported with bwrap
        eb_options.append('--robot')

    # GPU installations
    # determine if the installation is GPU software
    # (GPU component or toolchain name in the easyconfig filename)
    gpu_software = False
    for path in opts.easyconfigs:
        filename = os.path.basename(path)
        if any(x in filename for x in hooks_hydra.GPU_COMPONENTS + hooks_hydra.GPU_TOOLCHAINS):
            logger.info("GPU software detected in %s", filename)
            gpu_software = True

    # GPU software, or forced with --gpu force*, use the GPU partition on archs
    # that support it (unless the user explicitly gave a partition)
    use_gpu_partition = not opts.partition and (gpu_software or opts.gpu in ('force', 'force-nodevice'))

    # option --gpu with *-nodevice options do not request a GPU device;
    # * detect mode, only for jobs that are sent to a GPU partition (i.e. GPU software)
    # * force mode, all jobs
    # (exception: partition with gpu_required override this setting)
    gpu_device_requested = opts.gpu == 'force' or (opts.gpu == 'detect' and gpu_software)

    # Extra EB settings from user
    if opts.extra_eb_flags:
        eb_options.append(opts.extra_eb_flags)

    # ---> main build + lmod cache loop <--- #
    # submit build jobs for each micro-architecture
    for (host_arch, host_partition) in build_hosts:
        job_options = dict(job)

        # set tmp dir and update build and install paths accordingly
        if opts.tmp == 'tmp':
            job_options['tmp'] = '/tmp'
        elif opts.tmp == 'scratch':
            job_options['tmp'] = os.path.join('$VSC_SCRATCH_VO_USER', host_arch)
        ebconf['buildpath'] = os.path.join(job_options['tmp'], 'eb-submit-build')
        ebconf['installpath'] = os.path.join(APPS, MACHINE, '${VSC_OS_LOCAL:?}', host_arch)

        # per-job EB options (paths depend on the architecture)
        job_eb_options = eb_options + [f'--{opt}={path}' for opt, path in ebconf.items()]

        # set this job's partition and cluster
        job_partition = host_partition
        if use_gpu_partition:
            gpu_partition = ARCHS[MACHINE][host_arch]['partition']['gpu']
            if gpu_partition:
                job_partition = gpu_partition

        # partitions that require a GPU device get one, overriding the --gpu option
        job_gpu_device = PARTITIONS[job_partition]['gpu_required'] or gpu_device_requested

        # set Slurm directives in job file
        job_options.update(
            {
                'job_name': mk_job_name(easyconfig, host_arch),
                'host_arch': host_arch,
                'partition': job_partition,
                'cluster': PARTITIONS[job_partition]['cluster'],
                'walltime': PARTITIONS[job_partition]['walltime'] if not opts.job_small else SMALL_JOB['walltime'],
                'nodes': PARTITIONS[job_partition]['nodes'],
                'tasks': PARTITIONS[job_partition]['tasks'] if not opts.job_small else SMALL_JOB['tasks'],
                'gpus': PARTITIONS[job_partition]['gpus'] if job_gpu_device else '',
                'eb_options': " ".join(job_eb_options),
                'eb_buildpath': ebconf['buildpath'],
                'eb_installpath': ebconf['installpath'],
                'lmod_cache_cmd': make_cmd_lmod_cache(host_arch),
            }
        )

        # submit build job
        logger.debug('job_options: %s', job_options)

        logger.info(
            "Building %s on %s (%s)",
            easyconfig,
            job_options['partition'],
            host_arch,
        )

        ec, buildjob_out = submit_build_job(
            job_options,
            keep_job=opts.keep,
            sub_options=opts.extra_job_flags,
            cluster=job_options['cluster'],
            local_exec=local_exec,
            dry_run=dry_run,
        )

        if ec != 0:
            logger.error("Failed to submit or run build job for '%s': %s", easyconfig, buildjob_out)
            sys.exit(1)


if __name__ == '__main__':
    main()
