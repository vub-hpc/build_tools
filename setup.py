#!/usr/bin/env python3
#
# Copyright 2017-2023 Vrije Universiteit Brussel
# All rights reserved.
#
# This file is part of eb_hooks,
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
##
"""
eb_hooks base distribution setup.py

@author: Alex Domingo (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
"""
from vsc.install import shared_setup
from vsc.install.shared_setup import ad, sm, wp


PACKAGE = {
    'version': '1.1.4',
    'author': [ad, sm, wp],
    'maintainer': [ad, sm, wp],
    'setup_requires': [
        'vsc-install >= 0.15.3',
    ],
    'install_requires': [
        'easybuild',
    ],
    'python_requires': '~=3.6',
    'zip_safe': False,
    'url': "https://vub-hpc/eb_hooks",
}


if __name__ == '__main__':
    shared_setup.action_target(PACKAGE)
