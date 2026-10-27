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
Unit tests for build_tools.package

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import re

from build_tools import package


def test_package_metadata():
    assert re.fullmatch(r'\d+\.\d+\.\d+', package.VERSION)

    assert package.AUTHOR.keys() == package.AUTHOR_EMAIL.keys()
    for author in package.AUTHOR.values():
        assert author
    for email in package.AUTHOR_EMAIL.values():
        assert '@' in email
