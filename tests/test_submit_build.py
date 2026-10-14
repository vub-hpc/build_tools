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
Unit tests for bin/submit_build.py

The test cases cover every row of the GPU job submission tables in the
README; the tables define the expected results.

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import importlib.util
import os
import sys

import pytest

from build_tools import clusters

# easyconfig filenames for the two easyconfig types of the README tables
NON_GPU_EASYCONFIG = 'zlib-1.2.11.eb'
GPU_EASYCONFIG = 'zlib-1.2.11-CUDA-12.8.eb'

# one architecture per flavour, as in the README
CPU_ONLY_ARCH = 'zen3'        # no GPU partition
GPU_ONLY_ARCH = 'zen2-ib'     # CPU and GPU partition are the same
CPU_GPU_ARCH = 'zen5-ib'      # different CPU and GPU partitions

# rows of the README tables:
# (easyconfig type, --gpu option, GPU required, partition result, GPU device)
# (partition result 'cpu (same as gpu)' is normalized to 'cpu')
CPU_ONLY_ROWS = [
    ('non-gpu', 'detect', False, 'cpu', False),
    ('non-gpu', 'detect', True, 'cpu', False),
    ('non-gpu', 'detect-nodevice', False, 'cpu', False),
    ('non-gpu', 'detect-nodevice', True, 'cpu', False),
    ('non-gpu', 'force', False, 'cpu', False),
    ('non-gpu', 'force', True, 'cpu', False),
    ('non-gpu', 'force-nodevice', False, 'cpu', False),
    ('non-gpu', 'force-nodevice', True, 'cpu', False),
    ('gpu', 'detect', False, 'cpu', False),
    ('gpu', 'detect', True, 'cpu', False),
    ('gpu', 'detect-nodevice', False, 'cpu', False),
    ('gpu', 'detect-nodevice', True, 'cpu', False),
    ('gpu', 'force', False, 'cpu', False),
    ('gpu', 'force', True, 'cpu', False),
    ('gpu', 'force-nodevice', False, 'cpu', False),
    ('gpu', 'force-nodevice', True, 'cpu', False),
]

GPU_ONLY_ROWS = [
    ('non-gpu', 'detect', False, 'cpu', False),
    ('non-gpu', 'detect', True, 'cpu', True),
    ('non-gpu', 'detect-nodevice', False, 'cpu', False),
    ('non-gpu', 'detect-nodevice', True, 'cpu', True),
    ('non-gpu', 'force', False, 'gpu', True),
    ('non-gpu', 'force', True, 'gpu', True),
    ('non-gpu', 'force-nodevice', False, 'gpu', False),
    ('non-gpu', 'force-nodevice', True, 'gpu', True),
    ('gpu', 'detect', False, 'gpu', True),
    ('gpu', 'detect', True, 'gpu', True),
    ('gpu', 'detect-nodevice', False, 'gpu', False),
    ('gpu', 'detect-nodevice', True, 'gpu', True),
    ('gpu', 'force', False, 'gpu', True),
    ('gpu', 'force', True, 'gpu', True),
    ('gpu', 'force-nodevice', False, 'gpu', False),
    ('gpu', 'force-nodevice', True, 'gpu', True),
]

CPU_GPU_ROWS = [
    ('non-gpu', 'detect', False, 'cpu', False),
    ('non-gpu', 'detect', True, 'cpu', False),
    ('non-gpu', 'detect-nodevice', False, 'cpu', False),
    ('non-gpu', 'detect-nodevice', True, 'cpu', False),
    ('non-gpu', 'force', False, 'gpu', True),
    ('non-gpu', 'force', True, 'gpu', True),
    ('non-gpu', 'force-nodevice', False, 'gpu', False),
    ('non-gpu', 'force-nodevice', True, 'gpu', True),
    ('gpu', 'detect', False, 'gpu', True),
    ('gpu', 'detect', True, 'gpu', True),
    ('gpu', 'detect-nodevice', False, 'gpu', False),
    ('gpu', 'detect-nodevice', True, 'gpu', True),
    ('gpu', 'force', False, 'gpu', True),
    ('gpu', 'force', True, 'gpu', True),
    ('gpu', 'force-nodevice', False, 'gpu', False),
    ('gpu', 'force-nodevice', True, 'gpu', True),
]

FLAVOURS = (
    ('cpu-only', CPU_ONLY_ARCH, CPU_ONLY_ROWS),
    ('gpu-only', GPU_ONLY_ARCH, GPU_ONLY_ROWS),
    ('cpu-gpu', CPU_GPU_ARCH, CPU_GPU_ROWS),
)

CASES = [
    (flavour, arch, ec_type, gpu_option, gpu_required, exp_kind, exp_device)
    for (flavour, arch, rows) in FLAVOURS
    for (ec_type, gpu_option, gpu_required, exp_kind, exp_device) in rows
]


@pytest.fixture(scope='module')
def submit_build():
    """load bin/submit_build.py as a module"""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(repo_root, 'bin', 'submit_build.py')
    spec = importlib.util.spec_from_file_location('submit_build', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_submit_build(submit_build, monkeypatch, tmp_path, arch, gpu_option, easyconfig, gpu_required):
    """run submit_build.main() in dry-run mode and return the submitted job options"""
    # set the GPU required state of the arch partitions as in the table row
    arch_props = clusters.ARCHS[clusters.MACHINE][arch]
    for partition in {arch_props['partition']['cpu'], arch_props['partition']['gpu']}:
        if partition is not None:
            monkeypatch.setitem(clusters.PARTITIONS[partition], 'gpu_required', gpu_required)

    # fake virtualenv with a vsc-software-stack repo next to it
    (tmp_path / 'venv').mkdir()
    (tmp_path / 'vsc-software-stack').mkdir()
    monkeypatch.setenv('VIRTUAL_ENV', str(tmp_path / 'venv'))

    monkeypatch.setattr(sys, 'argv', ['submit_build.py', '-D', '-a', arch, '-g', gpu_option, easyconfig])

    job_options_list = []

    def fake_submit_build_job(job_options, **kwargs):
        job_options_list.append(dict(job_options))
        return 0, ''

    monkeypatch.setattr(submit_build, 'submit_build_job', fake_submit_build_job)

    submit_build.main()

    assert len(job_options_list) == 1
    return job_options_list[0]


@pytest.mark.parametrize(
    'flavour,arch,ec_type,gpu_option,gpu_required,exp_kind,exp_device',
    CASES,
    ids=[f'{flavour}-{ec}-{option}-required-{int(required)}'
         for (flavour, _arch, ec, option, required, _kind, _device) in CASES]
)
def test_gpu_job_submission(submit_build, monkeypatch, tmp_path,
                            flavour, arch, ec_type, gpu_option, gpu_required, exp_kind, exp_device):
    easyconfig = NON_GPU_EASYCONFIG if ec_type == 'non-gpu' else GPU_EASYCONFIG

    job_options = _run_submit_build(
        submit_build, monkeypatch, tmp_path, arch, gpu_option, easyconfig, gpu_required
    )

    exp_partition = clusters.ARCHS[clusters.MACHINE][arch]['partition'][exp_kind]
    assert job_options['partition'] == exp_partition
    assert bool(job_options['gpus']) == exp_device
