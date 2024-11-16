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
Unit tests configuration file

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import pytest

from easybuild.tools.options import set_up_configuration


def pytest_addoption(parser):
    parser.addoption(
        '--fromsource', action='store_true', help='run the tests on the source tree without installing first')


@pytest.fixture
def get_module_cmd(request):
    fromsource = request.config.getoption('fromsource')
    if fromsource:
        return '../bin/ec2ml.py'
    else:
        return 'ec2ml.py'


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def inputdir(rootdir):
    return os.path.join(rootdir, 'input')


def realpath_apps_brussel(path):
    return path.replace('/apps/brussel', '/vscmnt/brussel_pixiu_apps/_apps_brussel')


@pytest.fixture
def mock_realpath_apps_brussel(monkeypatch):
    monkeypatch.setattr('os.path.realpath', realpath_apps_brussel)


@pytest.fixture
def set_up_config():
    set_up_configuration(silent=True)
    yield
