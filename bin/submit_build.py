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
from build_tools.clusters import (ANANSI, APPS, ARCHS, BRUSSEL, GENT, MACHINE, PARTITIONS, SOFIA, SOURCES)
from build_tools.hooks_hydra import (
    SUBDIR_MODULES_BWRAP,
    SUFFIX_MODULES_PATH,
    SUFFIX_MODULES_SYMLINK,
    VALID_MODULES_SUBDIRS,
)
from build_tools.lmodtools import submit_lmod_cache_job
from build_tools.package import VERSION
from build_tools.softinstall import mk_job_name, run_no_shell, submit_build_job

logger = stdlib_logger(__name__)
logging.basicConfig(level=logging.INFO)


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

VSC_DEFAULT_CLUSTER_MODULE = os.getenv('VSC_DEFAULT_CLUSTER_MODULE')
if not VSC_DEFAULT_CLUSTER_MODULE:
    logger.error("VSC_DEFAULT_CLUSTER_MODULE environment variable is undefined")
    sys.exit(1)

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

    venv = os.getenv('VIRTUAL_ENV')
    if not venv:
        logger.error("VIRTUAL_ENV environment variable is undefined, "
                     "please activate the build_tools virtual environment")
        sys.exit(1)
    vscsoftstack_root = os.path.join(os.path.dirname(venv), 'vsc-software-stack')

    # Default job options
    job = {
        'appsmnt': '/vscmnt/brussel_pixiu_apps/_apps_brussel',
        'bwrap': '0',
        'cluster': VSC_DEFAULT_CLUSTER_MODULE,
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

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Submit easyconfig as jobs to all different architectures.')
    parser.add_argument('-a', '--arch', type=strlist, default=None,
                        help='CPU architecture of the host system and the build')
    parser.add_argument('-b', '--bwrap', action='store_true',
                        help='Reinstall in 2 steps via new namespace with bwrap (no robot)')
    parser.add_argument('-c', '--clang', action='store_true', help='Set LANG=C in the build (instead of unicode)')
    parser.add_argument('-d', '--debug', action='store_true', help='Set log level to DEBUG (default is INFO)')
    parser.add_argument('-D', '--dry-run', action='store_true', help='Do not fetch/install, set debug log level')
    parser.add_argument('-e', '--extra-flags', default=None, help='Extra flags to pass to EasyBuild')
    parser.add_argument('-f', '--extra-mod-footer', default=None, help='Path to extra footer for module file')
    parser.add_argument('-q', '--extra-sub-flags', default='', help='Extra flags to pass to Slurm')
    parser.add_argument('-g', '--gpu', action='store_true', help='Request a GPU in the GPU partitions')
    parser.add_argument('-k', '--keep', action='store_true', help='Do not delete the job file at the end')
    parser.add_argument('-o', '--lmod-cache-only', action='store_true',
                        help='Run Lmod cache and exit, no software installation')
    parser.add_argument('-l', '--local', action='store_true', help='Do not submit as job, run locally')
    parser.add_argument('-P', '--partition', type=strlist, default=None, help='Slurm partition for the build')
    parser.add_argument('-n', '--pre-fetch', action='store_true',
                        help='Pre-fetch sources before submitting build jobs')
    parser.add_argument('-p', '--pwd-robot-append', action='store_true',
                        help='Append current working dir to robot path')
    parser.add_argument('-s', '--skip-lmod-cache', action='store_true',
                        help='Do not run Lmod cache after installation')
    parser.add_argument('-m', '--tmp', action='store_true', help='Use /tmp as temporary disk instead of /dev/shm')
    parser.add_argument('-M', '--tmp-scratch', action='store_true',
                        help='Use VSC_SCRATCH_VO_USER as temporary disk instead of /dev/shm')
    parser.add_argument('-v', '--version', action='store_true', help='Show the version')
    parser.add_argument('easyconfigs', nargs='*', help='easyconfig file(s) to install')
    opts = parser.parse_args()

    if opts.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if opts.version:
        print(VERSION)
        sys.exit(0)

    dry_run = opts.dry_run
    if dry_run:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info('Doing a dry-run, no fetch/install/lmod-cache')

    if opts.lmod_cache_only:
        for arch in DEFAULT_ARCHS:
            submit_lmod_cache_job(ARCHS[MACHINE][arch]['partition']['cpu'], dry_run=dry_run)
        sys.exit(0)

    if not opts.easyconfigs:
        logger.error("No easyconfig is given...")
        sys.exit(1)

    if not os.path.isdir(vscsoftstack_root):
        logger.error(
            f"Cannot locate 'vsc-software-stack' repo in: {vscsoftstack_root} - "
            "Please clone that repo in the parent folder of your virtual environment directory"
        )
        sys.exit(1)

    easyconfig = ' '.join(opts.easyconfigs)
    job['easyconfig'] = easyconfig
    logger.info("Preparing to install %s", easyconfig)

    # Set host archs: define arch_stack
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

    # Set Slurm partitions: define build_hosts
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
    if opts.clang:
        job['langcode'] = 'C'

    # Set robot paths
    if opts.pwd_robot_append:
        ebconf['robot-paths'] += ':' + os.getcwd()
    job['robot_paths'] = ebconf['robot-paths']

    # Add extra footer
    if opts.extra_mod_footer:
        # if explicitly requested
        if os.path.exists(opts.extra_mod_footer):
            job['extra_mod_footer'] = opts.extra_mod_footer
        else:
            logger.error("Could not find extra footer: %s", opts.extra_mod_footer)
            sys.exit(1)

    if opts.pre_fetch:
        # fetch sources before submitting build jobs
        fetch_opts = ['--stop=fetch', '--robot', '--ignore-locks']
        if opts.extra_flags:
            fetch_opts.append(opts.extra_flags)
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

    bwrap = opts.bwrap
    if bwrap:
        job['bwrap'] = 1

    if opts.skip_lmod_cache:
        job['lmod_cache'] = '0'
        logger.info("Not running Lmod cache after installation")

    # ---> main build + lmod cache loop <--- #
    # submit build jobs for each micro-architecture
    for (host_arch, host_partition) in build_hosts:
        job_options = dict(job)
        job_options['host_arch'] = host_arch
        job_options['lmod_json_spider_cache'] = ARCHS[MACHINE][host_arch].get('lmod_json_spider_cache', '0')

        # Set tmp dir and update build path accordingly
        if opts.tmp:
            job_options['tmp'] = '/tmp'
        elif opts.tmp_scratch:
            job_options['tmp'] = os.path.join('$VSC_SCRATCH_VO_USER', host_arch)
        ebconf['buildpath'] = os.path.join(job_options['tmp'], 'eb-submit-build')

        # common EB command line options
        eb_options = [
            '--logtostdout',
            '--module-extensions',
            '--zip-logs=bzip2',
            '--module-depends-on',
            f'--suffix-modules-path={SUFFIX_MODULES_PATH}',
            f'--moduleclasses={",".join(os.path.join(x, SUFFIX_MODULES_SYMLINK) for x in VALID_MODULES_SUBDIRS)}',
        ]
        if opts.debug:
            eb_options.append('--debug')

        if bwrap:
            eb_options.extend([
                '--rebuild',
                f'--subdir-modules={SUBDIR_MODULES_BWRAP}',
            ])
        else:
            # robot is not supported with bwrap
            eb_options.append('--robot')

        # extra settings from user
        if opts.extra_flags:
            eb_options.append(opts.extra_flags)

        # update build and install paths of the EB job
        install_dir = host_arch
        ebconf['installpath'] = os.path.join(APPS, MACHINE, '${VSC_OS_LOCAL:?}', install_dir)
        for opt, path in ebconf.items():
            eb_options.append(f'--{opt}={path}')

        cluster = PARTITIONS[host_partition].get('cluster', VSC_DEFAULT_CLUSTER_MODULE)

        # set Slurm directives in job file
        job_options.update(
            {
                'job_name': mk_job_name(easyconfig, host_arch),
                'walltime': PARTITIONS[host_partition]['walltime'],
                'nodes': PARTITIONS[host_partition]['nodes'],
                'tasks': PARTITIONS[host_partition]['tasks'],
                'gpus': '',
                'partition': host_partition,
                'cluster': cluster,
                'eb_options': " ".join(eb_options),
                'eb_buildpath': ebconf['buildpath'],
                'eb_installpath': ebconf['installpath'],
            }
        )

        # settings for builds with GPUs
        if opts.gpu:
            if ARCHS[MACHINE][host_arch]['partition']['gpu']:
                # user specified partitions have priority
                if not opts.partition:
                    # install on GPU partition on archs with GPUs
                    job_options['partition'] = ARCHS[MACHINE][host_arch]['partition']['gpu']
                    if cluster != SOFIA:
                        job_options['cluster'] = PARTITIONS[job_options['partition']].get('cluster',
                                                                                          VSC_DEFAULT_CLUSTER_MODULE)
                if job_options['cluster'] == ANANSI:
                    job_options['gpus'] = '--gres=shard:1'
                else:
                    job_options['gpus'] = '--gpus-per-node=1'

        # sofia zen4_h200 requires at least 1 GPU
        if cluster == SOFIA and host_partition == 'zen4_h200':
            job_options['gpus'] = '--gpus-per-node=1'

        # add extra footer if requested
        if opts.extra_mod_footer:
            job_options['eb_options'] += f' --modules-footer={job_options["extra_mod_footer"]}'

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
            sub_options=opts.extra_sub_flags,
            cluster=job_options['cluster'],
            local_exec=local_exec,
            dry_run=dry_run,
        )

        if ec != 0:
            logger.error("Failed to submit or run build job for '%s': %s", easyconfig, buildjob_out)
            sys.exit(1)


if __name__ == '__main__':
    main()
