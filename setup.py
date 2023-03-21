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

from pathlib import Path
import setuptools

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

PKG = {}
with open("src/eb_hooks/package.py", encoding='utf-8') as fh:
    exec(fh.read(), PKG)  # pylint: disable=exec-used

setuptools.setup(
    name="eb_hooks",
    version=PKG["VERSION"],
    author=', '.join(PKG["AUTHOR"].values()),
    author_email=', '.join(PKG["AUTHOR_EMAIL"].values()),
    description="EasyBuild hooks for HPC clusters ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://vub-hpc/eb_hooks",

    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),

    python_requires='~=3.6',
    install_requires=[
        'easybuild',
    ],
    tests_require=[
        'pytest',
    ],
    zip_safe=False,
)
