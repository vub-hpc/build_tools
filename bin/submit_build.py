#!/usr/bin/env python3
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
Script to submit easyconfig as jobs to all different architectures.

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import re
import sys

from vsc.utils import fancylogger
from vsc.utils.run import RunNoShell
from vsc.utils.script_tools import SimpleOption

from build_tools import hooks_hydra
from build_tools.clusters import ARCHS, PARTITIONS
from build_tools.filetools import APPS_BRUSSEL
from build_tools.hooks_hydra import (
    SUBDIR_MODULES_BWRAP,
    SUFFIX_MODULES_PATH,
    SUFFIX_MODULES_SYMLINK,
    VALID_MODULES_SUBDIRS,
)
from build_tools.lmodtools import submit_lmod_cache_job
from build_tools.package import VERSION
from build_tools.softinstall import mk_job_name, submit_build_job

logger = fancylogger.getLogger()
fancylogger.logToScreen(True)
fancylogger.setLogLevelInfo()

# repositories with easyconfigs
VSCSOFTSTACK_ROOT = os.path.join(os.path.dirname(os.getenv("VIRTUAL_ENV", "")), "vsc-software-stack")
EASYCONFIG_REPOS = [
    # our site repo (https://github.com/vscentrum/vsc-software-stack/tree/site-vub)
    os.path.join("site-vub", "easyconfigs"),
    "easybuild",  # main EasyBuild repo (https://github.com/easybuilders/easybuild-easyconfigs)
]
EASYBLOCK_REPO = os.path.join("site-vub", "easyblocks", "*", "*.py")

DEFAULT_ARCHS = [arch for (arch, prop) in ARCHS.items() if prop['default']]
LOCAL_ARCH = os.getenv('VSC_ARCH_LOCAL', '') + os.getenv('VSC_ARCH_SUFFIX', '')
if LOCAL_ARCH not in ARCHS:
    logger.error("Local system has unsupported architeture: '%s'", LOCAL_ARCH)
    sys.exit(1)


def main():
    """Submit job script to deploy software installation with EasyBuild"""

    # Default job options
    job = {
        'bwrap': '0',
        'cluster': 'hydra',
        'extra_mod_footer': None,
        'langcode': 'en_US.utf8',
        'lmod_cache': '1',
        'target_arch': None,
        'tmp': '/dev/shm',
    }

    # Easybuild default paths
    # start using environment from local machine, job scripts get custom paths
    ebconf = {
        'accept-eula-for': 'Intel-oneAPI,CUDA,cuDNN,NVHPC',
        'buildpath': os.path.join(job['tmp'], 'eb-submit-build-fetch'),
        'hooks': hooks_hydra.__file__,
        'include-easyblocks': os.path.join(VSCSOFTSTACK_ROOT, EASYBLOCK_REPO),
        'installpath': os.path.join(APPS_BRUSSEL, '${VSC_OS_LOCAL:?}', LOCAL_ARCH),
        'prefer-python-search-path': 'EBPYTHONPREFIXES',
        'robot-paths': ":".join([os.path.join(VSCSOFTSTACK_ROOT, repo) for repo in EASYCONFIG_REPOS]),
        'sourcepath': '/apps/brussel/sources:/apps/gent/source',
    }

    # Parse command line arguments
    options = {
        "arch": ("CPU architecture of the host system and the build", 'strlist', 'add', None, 'a'),
        "bwrap": ("Reinstall in 2 steps via new namespace with bwrap (no robot)", None, "store_true", False, 'b'),
        "clang": ("Set LANG=C in the build (instead of unicode)", None, "store_true", False, 'c'),
        "cross-compile": ("CPU architecture of the build (different than the build system)", None, "store", None, 'x'),
        "dry-run": ("Do not fetch/install, set debug log level", None, "store_true", False, 'D'),
        "extra-flags": ("Extra flags to pass to EasyBuild", None, "store", None, 'e'),
        "extra-mod-footer": ("Path to extra footer for module file", None, "store", None, 'f'),
        "extra-sub-flags": ("Extra flags to pass to Slurm", None, "store", '', 'q'),
        "gpu": ("Request a GPU in the GPU partitions", None, "store_true", None, 'g'),
        "keep": ("Do not delete the job file at the end", None, "store_true", False, 'k'),
        "lmod-cache-only": ("Run Lmod cache and exit, no software installation", None, "store_true", False, 'o'),
        "local": ("Do not submit as job, run locally", None, "store_true", False, 'l'),
        "partition": ("Slurm partition for the build", 'strlist', 'add', None, 'P'),
        "pre-fetch": ("Pre-fetch sources before submitting build jobs", None, "store_true", False, 'n'),
        "pwd-robot-append": ("Append current working dir to robot path", None, "store_true", False, 'p'),
        "skip-lmod-cache": ("Do not run Lmod cache after installation", None, "store_true", False, 's'),
        "tmp": ("Use /tmp as temporary disk instead of /dev/shm", None, "store_true", False, 'm'),
        "tmp-scratch": ("Use $VSC_SCRATCH as temporary disk instead of /dev/shm", None, "store_true", False, 'M'),
        "version": ("Show the version", None, "store_true", False, 'v'),
    }
    opts = SimpleOption(options)

    if opts.options.version:
        print(VERSION)
        sys.exit(0)

    dry_run = opts.options.dry_run
    if dry_run:
        fancylogger.setLogLevelDebug()
        logger.info('Doing a dry-run, no fetch/install/lmod-cache')

    if opts.options.lmod_cache_only:
        for arch in DEFAULT_ARCHS:
            submit_lmod_cache_job(ARCHS[arch]['partition']['cpu'], dry_run=dry_run)
        sys.exit(0)

    if not opts.args:
        logger.error("No easyconfig is given...")
        sys.exit(1)

    if not os.path.isdir(VSCSOFTSTACK_ROOT):
        logger.error(
            f"Cannot locate 'vsc-software-stack' repo in: {VSCSOFTSTACK_ROOT} - "
            "Please clone that repo in the parent folder of your virtual environment directory"
        )
        sys.exit(1)

    easyconfig = ' '.join(opts.args)
    job['easyconfig'] = easyconfig
    logger.info("Preparing to install %s", easyconfig)

    # Set host archs: define arch_stack
    local_exec = opts.options.local
    if local_exec:
        logger.info("Building on local architecture: %s", LOCAL_ARCH)
        arch_stack = [LOCAL_ARCH]
    elif opts.options.arch:
        arch_stack = opts.options.arch
        unknown_archs = [arch for arch in arch_stack if arch not in ARCHS]
        if unknown_archs:
            logger.error("Unknown archs: %s", ", ".join(unknown_archs))
            sys.exit(1)
    else:
        arch_stack = DEFAULT_ARCHS

    logger.debug("List of architectures: %s", arch_stack)

    # Set Slurm partitions: define build_hosts
    if opts.options.partition:
        # given list of partitions overwrites all other options
        partition_stack = [part for part in opts.options.partition if part in PARTITIONS]
        if opts.options.arch:
            logger.warning("Overwriting given architectures with the architectures of given partitions")
        arch_stack = [PARTITIONS[part]['arch'] for part in partition_stack]
        build_hosts = list(zip(arch_stack, partition_stack))
    else:
        # initially target default CPU partitions for all selected architectures
        # in case of builds for GPUs, the build host might change down the line if suitable GPU partitions exist
        build_hosts = [(arch, ARCHS[arch]['partition']['cpu']) for arch in arch_stack]

    # remove duplicates and clean-up list of build hosts
    build_hosts = {(arch, part) for (arch, part) in build_hosts if arch and part}

    logger.debug("Initial target build hosts: %s", ', '.join([f'{p} ({a})' for (a, p) in build_hosts]))

    # Cross compilation
    if opts.options.cross_compile:
        if len(build_hosts) > 1:
            logger.error("Cross-compilation only supports 1 build architecture (--arch)")
        target_arch = opts.options.cross_compile
        if target_arch not in ARCHS:
            logger.error("Unknown target arch: %s", target_arch)
            sys.exit(1)
        job['target_arch'] = target_arch
        logger.info("Doing cross-compilation to target arch: %s", job['target_arch'])

    # Switch build language to C
    if opts.options.clang:
        job['langcode'] = 'C'

    # Set robot paths
    if opts.options.pwd_robot_append:
        ebconf['robot-paths'] += ':' + os.getcwd()
    job['robot_paths'] = ebconf['robot-paths']

    # Add extra footer
    if opts.options.extra_mod_footer:
        # if explicitly requested
        if os.path.exists(opts.options.extra_mod_footer):
            job['extra_mod_footer'] = opts.options.extra_mod_footer
        else:
            logger.error("Could not find extra footer: %s", opts.options.extra_mod_footer)
            sys.exit(1)

    if opts.options.pre_fetch:
        # fetch sources before submitting build jobs
        fetch_opts = ['--stop=fetch', '--robot', '--ignore-locks']
        if opts.options.extra_flags:
            fetch_opts.append(opts.options.extra_flags)
        for opt, path in ebconf.items():
            # exclude --hooks and empty options from the fetch command
            if opt not in ['hooks'] and path is not None:
                fetch_opts.append(f'--{opt}={path}')
        if dry_run:
            fetch_opts.append('-x')  # extended dry-run

        fetch_cmd = f'eb {" ".join(fetch_opts)} {easyconfig}'

        logger.info("Fetching missing sources for %s and its dependencies...", easyconfig)
        ec, out = RunNoShell.run(fetch_cmd)

        if dry_run:
            logger.debug(out)
        elif ec == 0:
            out_msg = re.findall('Build succeeded.*', out)
            out_msg = "\n".join(out_msg).replace('Build succeeded', 'Sources are ready')
            logger.info(out_msg)
        else:
            logger.error("Failed to fetch sources for %s: %s", easyconfig, out)
            sys.exit(1)

    bwrap = opts.options.bwrap
    if bwrap:
        job['bwrap'] = 1

    if opts.options.skip_lmod_cache:
        job['lmod_cache'] = '0'
        logger.info("Not running Lmod cache after installation")

    # ---> main build + lmod cache loop <--- #
    # submit build jobs for each micro-architecture
    for (host_arch, host_partition) in build_hosts:
        job_options = dict(job)

        # without special target arch, target host arch
        if not job_options['target_arch']:
            job_options['target_arch'] = host_arch

        # Set tmp dir and update build path accordingly
        if opts.options.tmp:
            job['tmp'] = '/tmp'
        elif opts.options.tmp_scratch:
            job['tmp'] = os.path.join('$VSC_SCRATCH', job_options['target_arch'])
        ebconf['buildpath'] = os.path.join(job['tmp'], 'eb-submit-build')

        # common EB command line options
        eb_options = [
            '--logtostdout',
            '--debug',
            '--module-extensions',
            '--zip-logs=bzip2',
            '--module-depends-on',
            f'--suffix-modules-path={SUFFIX_MODULES_PATH}',
            f'--moduleclasses={",".join(os.path.join(x, SUFFIX_MODULES_SYMLINK) for x in VALID_MODULES_SUBDIRS)}',
        ]

        if bwrap:
            eb_options.extend([
                '--rebuild',
                f'--subdir-modules={SUBDIR_MODULES_BWRAP}',
            ])
        else:
            # robot is not supported with bwrap
            eb_options.append('--robot')

        # cross-compilation
        if job_options['target_arch'] != host_arch:
            eb_options.extend(['--optarch', ARCHS[job_options['target_arch']]['opt']])

        # extra settings from user
        if opts.options.extra_flags:
            eb_options.append(opts.options.extra_flags)

        # update build and install paths of the EB job
        install_dir = job_options['target_arch']
        ebconf['installpath'] = os.path.join(APPS_BRUSSEL, '${VSC_OS_LOCAL:?}', install_dir)
        for opt, path in ebconf.items():
            eb_options.append(f'--{opt}={path}')

        # set Slurm directives in job file
        job_options.update(
            {
                'job_name': mk_job_name(easyconfig, host_arch, job_options['target_arch']),
                'walltime': '23:59:59',
                'nodes': 1,
                'tasks': 4,
                'gpus': 0,
                'partition': host_partition,
                'cluster': PARTITIONS[host_partition].get('cluster', 'hydra'),
                'eb_options': " ".join(eb_options),
                'eb_buildpath': ebconf['buildpath'],
                'eb_installpath': ebconf['installpath'],
            }
        )

        # settings for builds with GPUs
        if opts.options.gpu:
            if ARCHS[host_arch]['partition']['gpu']:
                # install on GPU partition on archs with GPUs
                job_options['partition'] = ARCHS[host_arch]['partition']['gpu']
                job_options['gpus'] = 1

        # add extra footer if requested
        if opts.options.extra_mod_footer:
            job_options['eb_options'] += f' --modules-footer={job_options["extra_mod_footer"]}'

        # submit build job
        buildjob_out = None

        if job_options['partition']:
            logger.debug('job_options: %s', job_options)

            logger.info(
                "Building %s on %s (%s) for %s",
                easyconfig,
                job_options['partition'],
                host_arch,
                job_options['target_arch'],
            )

            ec, buildjob_out = submit_build_job(
                job_options,
                keep_job=opts.options.keep,
                sub_options=opts.options.extra_sub_flags,
                cluster=job_options['cluster'],
                local_exec=local_exec,
                dry_run=dry_run,
            )

            if ec != 0:
                logger.error("Failed to submit or run build job for '%s': %s", easyconfig, buildjob_out)
                sys.exit(1)


if __name__ == '__main__':
    main()
