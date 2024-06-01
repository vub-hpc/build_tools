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
Helper functions to handle temp files and dummy modules

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os
import re
import sys
import tempfile

from vsc.utils import fancylogger
from vsc.utils.run import RunNoShell


logger = fancylogger.getLogger()

APPS_BRUSSEL = os.path.join(os.path.sep, 'apps', 'brussel')


def write_tempfile(contents):
    """
    Helper function to write tmp file, it returns the actual filename
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as handle:
            handle.write(contents)
    except IOError as err:
        logger.error("Error writing tmp file: %s", err)
        sys.exit(1)

    return handle.name


def clean_append(filepath, new_content):
    """
    Use first and last line of content to match block of text from existing file
    Remove any existing content and append new content to clean file
    - filepath: (string) path to new or existing file
    - new_content: (string) content to be added to the file
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as handle:
            existing_content = handle.read()
    except IOError as err:
        existing_content = ''
        logger.debug("File does not exits, creating it: %s", filepath)

    if existing_content:
        # clean up the existing file content of any previous text matching new content
        # use first and last line in new content to match any block text
        boundaries = new_content.split('\n')
        boundaries = (re.escape(boundaries[0]), re.escape(boundaries[-1]))
        block_pattern = re.compile('^%s.*%s$' % boundaries, re.MULTILINE | re.DOTALL)
        existing_content = block_pattern.sub('', existing_content)

    # update/create file with new content
    file_content = existing_content + new_content
    try:
        with open(filepath, 'w+', encoding='utf-8') as handle:
            handle.write(file_content)
    except IOError as err:
        logger.error("Error writing file '%s': %s", filepath, err)
        sys.exit(1)
    else:
        logger.debug("Successfully appended data to: %s", filepath)


def poke(filename):
    """
    Update timestamp of existing file to current time
    """
    try:
        os.utime(filename, None)
    except OSError as err:
        if err.errno == 2:
            logger.error("Could not update timestamp of '%s', file does not exist", filename)
        elif err.errno == 13:
            logger.error("Could not update timestamp of '%s', permission denied", filename)
        else:
            logger.error("Could not update timestamp of '%s', unknown error", filename)
        sys.exit(1)
    else:
        return True


def install_dummy_module(easyconfig, module_path, footer, robot_paths, install_cmd='install_dummy_module.py',
                         dry_run=False):
    """
    Install a dummy module with provided footer
    """
    # let EB find the easyconfig and copy it to a tmp file
    temp_ec = write_tempfile('')
    copy_cmd = f"eb {easyconfig} --copy-ec {temp_ec} --robot-paths {robot_paths}"
    log_msg = f"Copying easyconfig {easyconfig} to {temp_ec}..."
    if dry_run:
        logger.info("(DRY RUN) %s", log_msg)
        ec, out = 0, log_msg
    else:
        logger.debug(log_msg)
        ec, out = RunNoShell.run(copy_cmd)

    # use EB functions to obtain module name/version and install it
    # this must be an external script due to option parsing conflicts between EB and submit_build.py
    install_cmd += f" {temp_ec} {module_path} {footer}"
    log_msg = f"Installing dummy module to {module_path}..."
    if dry_run:
        logger.info("(DRY RUN) %s", log_msg)
        ec, out = 0, log_msg
    else:
        logger.info(log_msg)
        ec, out = RunNoShell.run(install_cmd)

    return ec, out


def get_module(easyconfig, cmd='get_module_from_easyconfig.py'):
    """
    Get module name and version from an easyconfig file
    @return: (exit_code, [module_name, module_version])
    """
    # let EB find the easyconfig and copy it to a tmp file
    temp_ec = write_tempfile('')
    copy_cmd = "eb %s --copy-ec %s" % (easyconfig, temp_ec)
    log_msg = "Copying easyconfig %s to %s..." % (easyconfig, temp_ec)
    logger.debug(log_msg)
    ec, out = RunNoShell.run(copy_cmd)

    # use EB functions to obtain module name/version
    # this must be an external script due to option parsing conflicts between EB and submit_build.py
    cmd += " %s" % temp_ec
    ec, out = RunNoShell.run(cmd)

    return ec, out.splitlines()[-1].split('/')
