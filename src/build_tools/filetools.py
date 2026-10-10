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
Helper functions to handle temp files

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import logging
import sys
import tempfile

logger = logging.getLogger(__name__)


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
