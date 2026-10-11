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
Unit tests for build_tools.hooks_hydra

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import contextlib
import logging
import types

import pytest

from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.hooks import SANITYCHECK_STEP

from build_tools import hooks_hydra

# valid (sub)toolchain-version combinations per toolchain generation,
# as computed by calc_toolchain_versions.py from the installed easyconfigs
TC_VERSIONS = {
    '2024a': {
        'toolchains': [
            {'name': 'foss', 'version': '2024a'},
            {'name': 'gfbf', 'version': '2024a'},
            {'name': 'GCC', 'version': '13.3.0'},
            {'name': 'GCCcore', 'version': '13.3.0'},
            {'name': 'intel', 'version': '2024a'},
            {'name': 'intel-compilers', 'version': '2024.2.0'},
        ],
        'subdir': '2024a',
    },
    '2025a': {
        'toolchains': [
            {'name': 'foss', 'version': '2025a'},
            {'name': 'GCC', 'version': '14.2.0'},
            {'name': 'GCCcore', 'version': '14.2.0'},
            {'name': 'intel', 'version': '2025a'},
            {'name': 'intel-compilers', 'version': '2025.1.1'},
        ],
        'subdir': '2025a',
    },
    '25.1': {
        'toolchains': [
            {'name': 'nvidia-compilers', 'version': '25.1'},
            {'name': 'NVHPC', 'version': '25.1'},
        ],
        'subdir': '2024a',
    },
    '25.3-CUDA-12.8.0': {
        'toolchains': [
            {'name': 'nvidia-compilers', 'version': '25.3-CUDA-12.8.0'},
            {'name': 'NVHPC', 'version': '25.3-CUDA-12.8.0'},
        ],
        'subdir': '2025a',
    },
}


@pytest.fixture
def tc_versions():
    """
    Populate TC_VERSIONS with a known set of toolchain versions,
    without running calc_toolchain_versions.py in a subprocess
    """
    hooks_hydra.TC_VERSIONS.update(TC_VERSIONS)
    yield
    hooks_hydra.TC_VERSIONS.clear()


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
        ('nvidia-compilers', '25.1', 'GCCcore', '13.3.0', 'Toolchain', '2024a'),
        ('nvidia-compilers', '25.3-CUDA-12.8.0', 'GCCcore', '14.2.0', 'Toolchain', '2025a'),
        ('nvidia-compilers', '25.3', 'system', 'system', 'Toolchain', False),
        ('nvidia-compilers', '24.0', 'system', 'system', 'Toolchain', False),
        ('NVHPC', '25.1', 'GCCcore', '13.3.0', 'Toolchain', '2024a'),
        ('NVHPC', '25.3-CUDA-12.8.0', 'GCCcore', '14.2.0', 'Toolchain', '2025a'),
        ('NVHPC', '25.3', 'system', 'system', 'Toolchain', False),
        ('NVHPC', '24.0', 'system', 'system', 'Toolchain', False),
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
def test_calc_tc_gen_subdir(toolchain, tc_versions):
    name, version, tcname, tcversion, easyblock, expected_generation = toolchain
    generation, _ = hooks_hydra.calc_tc_gen_subdir(name, version, tcname, tcversion)

    assert generation == expected_generation


class FakeEasyconfig(dict):
    """minimal stand-in for an EasyConfig as used by the parse hook"""

    def __init__(self, name, toolchain_name='foss'):
        super().__init__(moduleclass=f'{name.lower()}/all', versionsuffix='')
        self.name = name
        self.version = '1.0'
        self.toolchain = types.SimpleNamespace(name=toolchain_name, version='2024a')
        self.log = logging.getLogger('test_parse_hook')


@pytest.fixture
def parse_hook_config(monkeypatch):
    """stub out EasyBuild configuration accessors used by the parse hook"""
    monkeypatch.setattr(hooks_hydra, 'ConfigurationVariables', lambda: {'subdir_modules': 'modules'})
    monkeypatch.setattr(hooks_hydra, 'build_option', lambda opt: None)


def test_parse_hook_gpu_unknown_arch(parse_hook_config, monkeypatch):
    monkeypatch.setattr(hooks_hydra, 'LOCAL_ARCH_FULL', 'bogus-arch')
    ec = FakeEasyconfig('CUDA')

    with pytest.raises(EasyBuildError, match='Unknown local architecture'):
        hooks_hydra.parse_hook(ec)


def test_parse_hook_gpu_dummy_module(parse_hook_config, monkeypatch):
    monkeypatch.setattr(hooks_hydra, 'LOCAL_ARCH_FULL', 'zen4')
    ec = FakeEasyconfig('CUDA')

    hooks_hydra.parse_hook(ec)

    assert ec['modluafooter'] == hooks_hydra.GPU_DUMMY_MOD_FOOTER
    assert ec['module_only'] is True
    assert ec['skipsteps'] == [SANITYCHECK_STEP]


def test_parse_hook_gpu_arch(parse_hook_config, monkeypatch):
    monkeypatch.setattr(hooks_hydra, 'LOCAL_ARCH_FULL', 'zen5-ib')
    ec = FakeEasyconfig('CUDA')

    hooks_hydra.parse_hook(ec)

    assert ec['cuda_compute_capabilities'] == hooks_hydra.ARCHS[hooks_hydra.MACHINE]['zen5-ib']['cuda_cc']


class FakeCfg(dict):
    """minimal stand-in for an EasyConfig parameter dict as used by the hooks"""
    easyblock = 'ConfigureMake'

    def disable_templating(self):
        return contextlib.nullcontext()


class FakeModuleContext:
    """minimal stand-in for the EasyBuild tool object in the pre-module hook"""

    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.cfg = FakeCfg()
        self.log = logging.getLogger('test_pre_module_hook')


def test_pre_module_hook_unknown_group(monkeypatch):
    def fake_getgrnam(name):
        raise KeyError(name)

    monkeypatch.setattr(hooks_hydra.grp, 'getgrnam', fake_getgrnam)
    tool = FakeModuleContext('VASP', '6.2.0')

    with pytest.raises(EasyBuildError, match='User group .* not found on this system'):
        hooks_hydra.pre_module_hook(tool)


def test_pre_module_hook_group(monkeypatch):
    monkeypatch.setattr(hooks_hydra.grp, 'getgrnam', lambda name: types.SimpleNamespace(gr_gid=1234))
    tool = FakeModuleContext('VASP', '6.2.0')

    hooks_hydra.pre_module_hook(tool)

    assert tool.group == ('bli_vasp6', 1234)


def test_set_tc_versions_script_not_found(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError(args[0][0])

    monkeypatch.setattr(hooks_hydra.subprocess, 'run', fake_run)

    with pytest.raises(RuntimeError, match='not found in PATH'):
        hooks_hydra.set_tc_versions()


def test_parse_hook_ib_missing_constant(parse_hook_config, monkeypatch):
    monkeypatch.setattr(hooks_hydra, 'EASYCONFIG_CONSTANTS', {})
    ec = FakeEasyconfig('UCX')
    ec['osdependencies'] = []
    ec.easyblock = 'ConfigureMake'

    with pytest.raises(EasyBuildError, match='OS_PKG_IBVERBS_DEV'):
        hooks_hydra.parse_hook(ec)


def test_parse_hook_ib_removes_ibverbs(parse_hook_config):
    pkg_ibverbs = hooks_hydra.EASYCONFIG_CONSTANTS['OS_PKG_IBVERBS_DEV'][0]
    ec = FakeEasyconfig('UCX')
    ec['osdependencies'] = [pkg_ibverbs, 'gcc']
    ec.easyblock = 'ConfigureMake'

    hooks_hydra.parse_hook(ec)

    assert ec['osdependencies'] == ['gcc']


@pytest.mark.parametrize(('arch_suffix', 'expected'), [
    ('-ib', "'--foo=bar baz' --with-verbs"),
    ('', "'--foo=bar baz' --without-verbs --without-rdmacm"),
])
def test_pre_configure_hook_ib_configopts(monkeypatch, arch_suffix, expected):
    monkeypatch.setattr(hooks_hydra, 'LOCAL_ARCH_SUFFIX', arch_suffix)
    tool = FakeModuleContext('UCX', '1.16.0')
    tool.cfg['configopts'] = '--with-verbs --foo="bar baz"'

    hooks_hydra.pre_configure_hook(tool)

    assert tool.cfg['configopts'] == expected
