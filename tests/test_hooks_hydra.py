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
        ('GCCcore', '13.3.0', 'system', 'system', 'Toolchain', '2024a'),
        ('GCCcore', '10.2.0', 'system', 'system', 'Toolchain', False),
        ('UCX-CUDA', '1.16.0', 'GCCcore', '13.3.0', 'EB_UCX_Plugins', '2024a'),
        ('STREAM', '5.10', 'intel-compilers', '2024.2.0', 'MakeCp', '2024a'),
        ('SAMtools', '1.21', 'GCC', '13.3.0', 'EB_SAMtools', '2024a'),
        # (software with) toolchains with generation as their version
        ('foss', '2024a', 'system', 'system', 'Toolchain', '2024a'),
        ('foss', '2021a', 'system', 'system', 'Toolchain', False),
        ('SciPy-bundle', '2024.05', 'gfbf', '2024a', 'EB_Bundle', '2024a'),
        ('R-bundle-CRAN', '2024.11', 'foss', '2024a', 'EB_R', '2024a'),
        # software with system toolchain
        ('zlib', '1.2.11', 'system', 'system', 'ConfigureMake', 'system'),
        ('MATLAB', '2023a', 'system', 'system', 'EB_MATLAB', 'system'),
        # (software with) unsupported toolchains
        ('torchvision', '0.9.1', 'fosscuda', '2022a', 'EB_torchvision', False),
        ('fosscuda', '2023a', 'system', 'system', 'Toolchain', False),
    ],
)
def test_calc_tc_gen_subdir(toolchain, set_up_config):
    name, version, tcname, tcversion, easyblock, expected_generation = toolchain
    generation, _ = hooks_hydra.calc_tc_gen_subdir(name, version, tcname, tcversion, easyblock)

    assert generation['toolchains'] == expected_generation
