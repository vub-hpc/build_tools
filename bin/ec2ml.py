#!/usr/bin/env python3
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
Helper script to extract the full module name from an easyconfig

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
import sys

from easybuild.framework.easyconfig.tools import det_easyconfig_paths, parse_easyconfigs
from easybuild.tools.options import set_up_configuration


def main():
    """Extract the full module name from the given easyconfigs"""
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: ec2ml.py <easyconfig> [<easyconfig>...]\n")
        sys.exit(1)

    set_up_configuration(silent=True)

    ec_paths = []
    for ec in sys.argv[1:]:
        paths = det_easyconfig_paths([ec])
        if not paths:
            sys.stderr.write(f"ERROR: easyconfig not found: {ec}\n")
            sys.exit(1)
        ec_paths.append(paths[0])

    easyconfigs, generated_ecs = parse_easyconfigs(list(zip(ec_paths, [False] * len(ec_paths))))

    full_mod_names = [x['full_mod_name'] for x in easyconfigs]

    print('\n'.join([f'full_mod_name {mod}' for mod in full_mod_names]))


if __name__ == "__main__":
    main()
