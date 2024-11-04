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
Unit tests for build_tools.softinstall

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import pytest

from build_tools import hooks_hydra


@pytest.mark.parametrize(
    'toolchain',
    [
        # (name, version, tcname, tcversion, easyblock, expected_generation)
        # (software with) toolchains with custom versioning
        ('GCCcore', '11.3.0', 'system', 'system', 'Toolchain', '2022a'),
        ('GCCcore', '10.2.0', 'system', 'system', 'Toolchain', False),
        ('UCX-CUDA', '1.14.1', 'GCCcore', '12.3.0', 'EB_UCX_Plugins', '2023a'),
        ('bwa-mem2', '2.2.1', 'intel-compilers', '2023.1.0', 'MakeCp', '2023a'),
        ('SAMtools', '1.18', 'GCC', '12.3.0', 'EB_SAMtools', '2023a'),
        # (software with) toolchains with generation as their version
        ('foss', '2023a', 'system', 'system', 'Toolchain', '2023a'),
        ('foss', '2021a', 'system', 'system', 'Toolchain', False),
        ('PyTorch', '2.1.2', 'foss', '2023a', 'EB_PyTorch', '2023a'),
        ('R', '4.3.2', 'gfbf', '2023a', 'EB_R', '2023a'),
        # software with system toolchain
        ('zlib', '1.2.11', 'system', 'system', 'ConfigureMake', 'system'),
        ('MATLAB', '2023a', 'system', 'system', 'EB_MATLAB', 'system'),
        # (software with) unsupported toolchains
        ('torchvision', '0.9.1', 'fosscuda', '2022a', 'EB_torchvision', False),
        ('fosscuda', '2023a', 'system', 'system', 'Toolchain', False),
    ],
)
def test_calc_tc_gen(toolchain, set_up_config):
    name, version, tcname, tcversion, easyblock, expected_generation = toolchain
    generation, _ = hooks_hydra.calc_tc_gen(name, version, tcname, tcversion, easyblock)

    assert generation == expected_generation
