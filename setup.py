#!/usr/bin/env python3
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
build_tools base distribution setup.py

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import setuptools

PKG = {}
with open("src/build_tools/package.py", encoding='utf-8') as fh:
    exec(fh.read(), PKG)

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name="build_tools",
    version=PKG["VERSION"],
    author=', '.join(PKG["AUTHOR"].values()),
    author_email=', '.join(PKG["AUTHOR_EMAIL"].values()),
    description="Tools to build and install software",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://vub-hpc/build_tools",

    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    scripts=[
        'bin/submit_build.py',
        'bin/install_dummy_module.py',
        'bin/get_module_from_easyconfig.py',
    ],

    python_requires='~=3.6',
    install_requires=[
        'vsc-base',
        'vsc-utils',
        'easybuild',
    ],
    tests_require=[
        'pytest',
    ],
    package_data={
        "build_tools": ["footers/*.footer"],
    },
    zip_safe=False,
)
