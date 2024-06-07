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


def bwrap_prefix(job_options, modname, install_dir):
    """
    Create the bwrap prefix command string
    :param job_options: dict with options to pass to job template
    :param modname: module name
    :param install_dir: architecture-specific installation subdirectory
    """

    bwrap_path = os.path.join(APPS_BRUSSEL, 'bwrap', '$VSC_OS_LOCAL', install_dir)
    real_installpath = os.path.realpath(job_options['eb_installpath'])
    mod_subdir = os.path.join('modules', job_options['tc_gen'], 'all', modname)
    soft_subdir = os.path.join('software', modname)

    soft_source = os.path.join(bwrap_path, soft_subdir)
    soft_dest = os.path.join(real_installpath, soft_subdir)

    mod_source = os.path.join(bwrap_path, mod_subdir)
    mod_dest = os.path.join(real_installpath, mod_subdir)

    if not os.path.isdir(soft_dest):
        logger.error("Bind destination does not exist: %s", soft_dest)

    return ' '.join([
        'mkdir -p %s &&' % soft_source,
        'mkdir -p %s &&' % mod_source,
        'bwrap',
        '--bind / /',
        '--bind %s %s' % (soft_source, soft_dest),
        '--bind %s %s' % (mod_source, mod_dest),
        '--dev /dev',
        '--bind /dev/log /dev/log',
    ])


def rsync_copy(job_options, modname, modversion, install_dir):
    """
    Create command string to copy the bwrap installation dir and module file to the real installation dir
    If the source and destination dirs are in the same filesystem,
        files are not copied but hardlinks are created (see rsync option --link-dest)
    :param job_options: dict with options to pass to job template
    :param modname: module name
    :param modversion: module version
    :param install_dir: architecture-specific installation subdirectory
    """
    source_path = os.path.join(APPS_BRUSSEL, 'bwrap', '$VSC_OS_LOCAL', install_dir)
    dest_path = job_options['eb_installpath']

    rel_soft_path = os.path.join('software', modname, modversion, '')  # trailing slash is required!

    source_soft_path = os.path.join(source_path, rel_soft_path)
    dest_soft_path = os.path.join(dest_path, rel_soft_path)

    rel_mod_path = os.path.join('modules', job_options['tc_gen'], 'all', modname)
    rel_mod_file = os.path.join(rel_mod_path, '%s.lua' % modversion)

    source_mod_path = os.path.join(source_path, rel_mod_path)
    source_mod_file = os.path.join(source_path, rel_mod_file)
    dest_mod_file = os.path.join(dest_path, rel_mod_file)

    rsync_software = ' '.join([
        'rsync -a',
        '--link-dest=%s' % source_soft_path,
        source_soft_path,
        dest_soft_path,
    ])
    rsync_module = ' '.join([
        'rsync -a',
        '--link-dest=%s' % source_mod_path,
        source_mod_file,
        dest_mod_file,
    ])
    return '\n'.join([
        'echo "bwrap install dir: %s"' % source_soft_path,
        'echo "destination install dir: %s"' % dest_soft_path,
        'echo "bwrap module file: %s"' % source_mod_file,
        'echo "destination module file: %s"' % dest_mod_file,
        'if [ ! -d %s ]; then echo "ERROR: bwrap install dir does not exist"; exit 1; fi' % source_soft_path,
        'if [ ! "$(ls -A %s)" ]; then echo "ERROR: bwrap install dir empty"; exit 1; fi' % source_soft_path,
        'if [ ! -s %s ]; then echo "ERROR: bwrap module file does not exist or empty"; exit 1; fi' % source_mod_file,
        rsync_software,
        'if [ $? -ne 0 ]; then echo "ERROR: failed to copy bwrap install dir"; exit 1; fi',
        rsync_module,
        'if [ $? -ne 0 ]; then echo "ERROR: failed to copy bwrap module file"; exit 1; fi',
        'rm -rf %s %s' % (source_soft_path, source_mod_file),
    ])
