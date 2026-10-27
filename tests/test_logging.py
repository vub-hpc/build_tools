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
Unit tests for the build_tools loggers

@author: Alex Domingo (Vrije Universiteit Brussel)
"""
import logging

import easybuild.tools.build_log  # noqa: F401 (sets logging.LoggerClass to EasyBuildLog)

from build_tools import clusters, filetools, lmodtools, softinstall, stdlib_logger

MODULES = [clusters, filetools, lmodtools, softinstall]


def test_stdlib_logger_returns_plain_logger():
    logger = stdlib_logger('build_tools.test.stdlib_logger')

    assert type(logger) is logging.Logger


def test_build_tools_loggers_are_plain_loggers():
    for module in MODULES:
        assert type(module.logger) is logging.Logger


def test_error_messages_are_not_rewritten(capfd):
    handler = logging.StreamHandler()
    logging.getLogger().addHandler(handler)

    try:
        for module in MODULES:
            module.logger.error(f"error message from {module.__name__}")
    finally:
        logging.getLogger().removeHandler(handler)

    stderr = capfd.readouterr().err
    for module in MODULES:
        assert f"error message from {module.__name__}" in stderr
    assert "EasyBuild encountered an error" not in stderr
