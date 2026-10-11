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
Tools to build and deploy installations with EasyBuild

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""
import logging


def stdlib_logger(name):
    """
    Return a plain standard library logger with the given name.

    EasyBuild's easybuild.tools.build_log sets logging.LoggerClass to
    EasyBuildLog at import time, so logging.getLogger() returns loggers
    whose error() messages are rewritten with "EasyBuild encountered an
    error". Demote the logger to a plain standard library Logger instance.
    """
    logger = logging.getLogger(name)
    if isinstance(logger, logging.Logger) and type(logger) is not logging.Logger:
        logger.__class__ = logging.Logger
    return logger
