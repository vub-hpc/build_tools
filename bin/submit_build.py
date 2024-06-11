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
from vsc.utils.script_tools import SimpleOption
from vsc.utils.run import RunNoShell

from build_tools import hooks_hydra
from build_tools.bwraptools import bwrap_prefix, rsync_copy
from build_tools.clusters import ARCHS, PARTITIONS
from build_tools.filetools import APPS_BRUSSEL, get_module
from build_tools.lmodtools import submit_lmod_cache_job
from build_tools.softinstall import mk_job_name, set_toolchain_generation, submit_build_job

# repositories with easyconfigs
VSCSOFTSTACK_ROOT = os.path.expanduser("~/vsc-software-stack")
EASYCONFIG_REPOS = [
    # our site repo (https://github.com/vscentrum/vsc-software-stack/tree/site-vub)
    os.path.join("site-vub", "easyconfigs"),
    "vsc",  # VSC repo (https://github.com/vscentrum/vsc-software-stack/tree/vsc)
    "easybuild",  # main EasyBuild repo (https://github.com/easybuilders/easybuild-easyconfigs)
]
EASYBLOCK_REPO = os.path.join("site-vub", "easyblocks", "*", "*.py")

logger = fancylogger.getLogger()
fancylogger.logToScreen(True)
fancylogger.setLogLevelInfo()

DEFAULT_ARCHS = [arch for (arch, prop) in ARCHS.items() if prop['default']]
LOCAL_ARCH = os.getenv('VSC_ARCH_LOCAL', '') + os.getenv('VSC_ARCH_SUFFIX', '')
if LOCAL_ARCH not in ARCHS:
    logger.error("Local system has unsupported architeture: '%s'", LOCAL_ARCH)
    sys.exit(1)


def main():
    """Submit job script to deploy software installation with EasyBuild"""

    # Default job options
    job = {
        'lmod_cache': '1',
        'langcode': 'en_US.utf8',
        'cluster': 'hydra',
        'target_arch': None,
        'extra_mod_footer': None,
        'tmp': '/dev/shm',
        'postinstall': '',
        'pre_eb_options': '',
    }

    # Easybuild default paths
    # start using environment from local machine, job scripts get custom paths
    ebconf = {
        'accept-eula-for': 'Intel-oneAPI,CUDA',
        'robot-paths': ":".join([os.path.join(VSCSOFTSTACK_ROOT, repo) for repo in EASYCONFIG_REPOS]),
        'include-easyblocks': os.path.join(VSCSOFTSTACK_ROOT, EASYBLOCK_REPO),
        'sourcepath': '/apps/brussel/sources:/apps/gent/source',
        'installpath': os.path.join(APPS_BRUSSEL, os.getenv('VSC_OS_LOCAL'), LOCAL_ARCH),
        'buildpath': os.path.join(job['tmp'], 'eb-submit-build-fetch'),
        'subdir-modules': 'modules',
        'hooks': hooks_hydra.__file__,
    }

    # Parse command line arguments
    options = {
        "arch": ("CPU architecture of the host system and the build", 'strlist', 'add', None, 'a'),
        "partition": ("Slurm partition for the build", 'strlist', 'add', None, 'P'),
        "toolchain": ("Toolchain generation of the installation", None, "store", None, 't'),
        "extra-flags": ("Extra flags to pass to EasyBuild", None, "store", None, 'e'),
        "extra-sub-flags": ("Extra flags to pass to Slurm", None, "store", '', 'q'),
        "extra-mod-footer": ("Path to extra footer for module file", None, "store", None, 'f'),
        "gpu": ("Request a GPU in the GPU partitions", None, "store_true", None, 'g'),
        "local": ("Do not submit as job, run locally", None, "store_true", False, 'l'),
        "keep": ("Do not delete the job file at the end", None, "store_true", False, 'k'),
        "clang": ("Set LANG=C in the build (instead of unicode)", None, "store_true", False, 'c'),
        "cross-compile": ("CPU architecture of the build (different than the build system)", None, "store", None, 'x'),
        "pwd-robot-append": ("Append current working dir to robot path", None, "store_true", False, 'p'),
        "tmp": ("Use /tmp as temporary disk instead of /dev/shm", None, "store_true", False, 'm'),
        "tmp-scratch": ("Use $VSC_SCRATCH as temporary disk instead of /dev/shm", None, "store_true", False, 'M'),
        "dry-run": ("Do not fetch/install, set debug log level", None, "store_true", False, 'D'),
        "skip-fetch": ("Do not fetch the sources, fail if they are missing", None, "store_true", False, 'n'),
        "bwrap": ("Reinstall via new namespace with bwrap", None, "store_true", False, 'b'),
        "skip-lmod-cache": ("Do not run Lmod cache after installation", None, "store_true", False, 's'),
        "lmod-cache-only": ("Run Lmod cache and exit, no software installation", None, "store_true", False, 'o'),
    }
    opts = SimpleOption(options)

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

    easyconfig = ' '.join(opts.args)
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
        arch_stack = [part['arch'] for part in partition_stack]
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

    # Set target toolchain generation
    job['tc_gen'] = set_toolchain_generation(easyconfig, user_toolchain=opts.options.toolchain)
    if not job['tc_gen']:
        logger.error("Unable to determine the toolchain generation, specify it with --toolchain")
        sys.exit(1)

    ebconf['subdir-modules'] = os.path.join('modules', job['tc_gen'])

    # Set robot paths
    if opts.options.pwd_robot_append:
        ebconf['robot-paths'] += ':' + os.getcwd()

    # Add extra footer
    if opts.options.extra_mod_footer:
        # if explicitly requested
        if os.path.exists(opts.options.extra_mod_footer):
            job['extra_mod_footer'] = opts.options.extra_mod_footer
        else:
            logger.error("Could not find extra footer: %s", opts.options.extra_mod_footer)
            sys.exit(1)

    if opts.options.skip_fetch:
        logger.info('Not fetching any sources')
    else:
        # fetch sources before submitting build jobs
        fetch_opts = ['--stop=fetch', '--robot', '--ignore-locks']
        if opts.options.extra_flags:
            fetch_opts.append(opts.options.extra_flags)
        for opt, path in ebconf.items():
            # exclude hooks and empty options from the fetch command
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
        logger.info('Reinstalling in 2 steps via new namespace under %s/bwrap', APPS_BRUSSEL)
        ec, module = get_module(easyconfig)
        if ec != 0:
            logger.error("Failed to get module name/version for %s", easyconfig)
            sys.exit(1)

    if opts.options.skip_lmod_cache:
        job['lmod_cache'] = ''
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

        # generate EB command line options
        eb_options = ['--robot', '--logtostdout', '--debug', '--module-extensions', '--zip-logs=bzip2']

        # cross-compilation
        if job_options['target_arch'] != host_arch:
            eb_options.extend(['--optarch', ARCHS[job_options['target_arch']]['opt']])

        # use depends_on in Lmod
        eb_options.append("--module-depends-on")

        # extra settings from user
        if opts.options.extra_flags:
            eb_options.append(opts.options.extra_flags)

        if opts.options.skip_fetch:
            # EB does not have an option for skipping the fetch step
            # as a workaround, fail hard when it tries to download missing sources
            eb_options.append('--download-timeout=-1')

        eb_options.append(easyconfig)

        # update build and install paths of the EB job
        install_dir = job_options['target_arch']
        ebconf['installpath'] = os.path.join(APPS_BRUSSEL, os.getenv('VSC_OS_LOCAL'), install_dir)
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

        # install in new namespace if requested
        if bwrap:
            job_options['eb_options'] += ' --rebuild'
            job_options['pre_eb_options'] = bwrap_prefix(job_options, module[0], install_dir)
            rsync_cmds = rsync_copy(job_options, module[0], module[1], install_dir)
            job_options['postinstall'] = '\n'.join([rsync_cmds, job_options['postinstall']])

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
