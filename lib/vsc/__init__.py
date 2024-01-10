#
# Copyright 2017-2024 Vrije Universiteit Brussel
#
# This file is part of eb_hooks,
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/vub-hpc/eb_hooks
#
# All rights reserved.
#
"""
Allow other packages to extend this namespace, zip safe setuptools style
@author: Andy Georges (Ghent University)
"""
import pkg_resources
pkg_resources.declare_namespace(__name__)
