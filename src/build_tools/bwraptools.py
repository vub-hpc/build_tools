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
Functions for installing in 2 steps:
1) install in new mount namespace under bwrap dir
2) copy from bwrap dir to real installation dir

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os

from vsc.utils import fancylogger

from build_tools.filetools import APPS_BRUSSEL

logger = fancylogger.getLogger()

BWRAP_PATH = os.path.join(APPS_BRUSSEL, 'bwrap', '$VSC_OS_LOCAL')
SUBDIR_MODULES_BWRAP = '.modules_bwrap'
MOD_FILEPATH_FILENAME = '{modversion}_fp.txt'


def bwrap_prefix(job_options, modname, arch):
    """
    Create the bwrap prefix command string
    :param job_options: dict with options to pass to job template
    :param modname: module name (without the version)
    :param arch: architecture-specific installation subdirectory
    """
    real_installpath = os.path.realpath(job_options['eb_installpath'])
    mod_subdir = os.path.join(SUBDIR_MODULES_BWRAP, 'all', modname)
    # cannot use 'software/<modname>/<modversion>' here, otherwise EB cannot "remove" the old installation
    soft_subdir = os.path.join('software', modname)

    soft_source = os.path.join(BWRAP_PATH, arch, soft_subdir)
    soft_dest = os.path.join(real_installpath, soft_subdir)

    mod_source = os.path.join(real_installpath, mod_subdir)

    if not os.path.isdir(soft_dest):
        logger.error("Bind destination does not exist: %s", soft_dest)

    # create a temporary dir for the module, but don’t bind it with bwrap:
    # the final location is not known yet, and module files don’t need a new namespace anyway
    return ' '.join([
        f'mkdir -p "{soft_source}" &&',
        f'mkdir -p "{mod_source}" &&',
        'bwrap',
        '--bind / /',
        f'--bind "{soft_source}" "{soft_dest}"',
        '--dev /dev',
        '--bind /dev/log /dev/log',
    ])


def rsync_copy(job_options, modname, modversion, arch):
    """
    Create command string to copy the bwrap installation dir and module file to the real installation dir
    If the source and destination dirs are in the same filesystem,
        files are not copied but hardlinks are created (see rsync option --link-dest)
    :param job_options: dict with options to pass to job template
    :param modname: module name
    :param modversion: module version
    :param arch: architecture-specific installation subdirectory
    """
    dest_path = job_options['eb_installpath']

    rel_soft_path = os.path.join('software', modname, modversion, '')  # trailing slash is required!

    source_soft_path = os.path.join(BWRAP_PATH, arch, rel_soft_path)
    dest_soft_path = os.path.join(dest_path, rel_soft_path)

    source_mod_path = os.path.join(dest_path, SUBDIR_MODULES_BWRAP, 'all', modname)
    source_mod_file = os.path.join(source_mod_path, f'{modversion}.lua')
    mod_filepath_file = os.path.join(source_mod_path, MOD_FILEPATH_FILENAME.format(modversion=modversion))

    rsync_software = ' '.join([
        'rsync -a',
        f'--link-dest="{source_soft_path}"',
        source_soft_path,
        dest_soft_path,
    ])
    rsync_module = ' '.join([
        'rsync -a',
        f'--link-dest="{source_mod_path}"',
        source_mod_file,
    ])
    return '\n'.join([
        f'dest_mod_file=$(<"{mod_filepath_file}")',
        f'echo "source install dir: {source_soft_path}"',
        f'echo "destination install dir: {dest_soft_path}"',
        f'echo "source module file: {source_mod_file}"',
        'echo "destination module file: $dest_mod_file"',
        f'test -d "{source_soft_path}" || {{ echo "ERROR: source install dir does not exist"; exit 1; }}',
        f'test -n "$(ls -A {source_soft_path})" || {{ echo "ERROR: source install dir is empty"; exit 1; }}',
        f'test -s "{source_mod_file}" || {{ echo "ERROR: source module file does not exist or is empty"; exit 1; }}',
        f'{rsync_software} || {{ echo "ERROR: failed to copy source install dir"; exit 1; }}',
        f'{rsync_module} "$dest_mod_file" || {{ echo "ERROR: failed to copy source module file"; exit 1; }}',
        f'rm -rf "{source_soft_path}" "{source_mod_file}" "{mod_filepath_file}"',
    ])
