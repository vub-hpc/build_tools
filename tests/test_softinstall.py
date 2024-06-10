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

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
import pytest

from build_tools import softinstall


@pytest.mark.parametrize(
    'toolchain',
    [
        ('GCCcore-10.2.0.eb', False, '2020b'),
        ('GCCcore-10.2.0.eb', '2020b', '2020b'),
        ('GCCcore-10.2.0.eb', '1920c', False),
        ('UCX-1.8.0-GCCcore-9.3.0-CUDA-11.0.2.eb', False, '2020a'),
        ('R-4.0.3-foss-2020b.eb', False, '2020b'),
        ('R-4.0.3-foss-2020b.eb', '2019a', '2019a'),
        ('TensorFlow-2.3.1-foss-2020a-Python-3.8.2.eb', False, '2020a'),
        ('TensorFlow-2.3.1-fosscuda-2020a-Python-3.8.2.eb', False, '2020a'),
        ('SAMtools-1.9-GCC-8.2.0-2.31.1.eb', False, '2019a'),
        ('SAMtools-1.9-iccifort-2019.1.144-GCC-8.2.0-2.31.1.eb', False, '2019a'),
    ],
)
def test_set_toolchain_generation(toolchain):
    easyconfig, user_toolchain, expected_generation = toolchain

    generation = softinstall.set_toolchain_generation(easyconfig, user_toolchain=user_toolchain)

    assert generation == expected_generation


@pytest.mark.parametrize(
    'test_name',
    [
        (
            'zlib-1.2.11',
            ['zlib-1.2.11.eb', None]
        ),
        (
            'zlib-1.2.11-skylake',
            ['zlib-1.2.11.eb', 'skylake']
        ),
        (
            'zlib-1.2.11-skylake-ivybridge',
            ['zlib-1.2.11.eb', 'skylake', 'ivybridge'],
        ),
        (
            'zlib-1.2.11-skylake',
            ['test/subdir/zlib-1.2.11.eb', 'skylake'],
        ),
        (
            'zlib-1.2.11-skylake',
            ['test/subdir/zlib-1.2.11.eb', 'skylake', 'skylake'],
        ),
    ]
)
def test_mk_job_name(test_name):
    (ref_name, job_args) = test_name
    job_name = softinstall.mk_job_name(*job_args)

    assert job_name == ref_name


@pytest.mark.parametrize(
    'test_job',
    [
        ('build_job_01.sh', {
            'job_name': 'test-job',
            'walltime': '23:59:59',
            'nodes': 1,
            'tasks': 4,
            'gpus': 0,
            'target_arch': 'skylake',
            'partition': 'skylake_mpi',
            'tc_gen': '2019a',
            'langcode': 'C',
            'eb_options': '',
            'pre_eb_options': '',
            'eb_buildpath': '/tmp/eb-test-build',
            'eb_installpath': '/apps/brussel/${VSC_OS_LOCAL}/skylake',
            'tmp': '/tmp/eb-test-build',
            'postinstall': '',
        }),
        ('build_job_02.sh', {
            'job_name': 'test-job-gpu',
            'walltime': '23:59:59',
            'nodes': 1,
            'tasks': 4,
            'gpus': 1,
            'target_arch': 'zen2',
            'partition': 'ampere_gpu',
            'tc_gen': '2020b',
            'langcode': 'C',
            'eb_options': ' --cuda-compute-capabilities=8.0',
            'pre_eb_options': 'bwrap',
            'eb_buildpath': '/tmp/eb-test-build',
            'eb_installpath': '/apps/brussel/${VSC_OS_LOCAL}/zen2-ib',
            'tmp': '/tmp/eb-test-build',
            'postinstall': 'rsync src dest',
        }),
    ]
)
def test_submit_build_job(inputdir, test_job):
    (job_script, job_options) = test_job
    sub_options = ''
    cluster = 'hydra'

    ec, out = softinstall.submit_build_job(
        job_options, keep_job=True, sub_options=sub_options, cluster=cluster, local_exec=False, dry_run=True
    )

    new_job = out.split(' ')[-1]
    with open(new_job) as nj:
        new_job_contents = nj.read().rstrip()

    ref_job = os.path.join(inputdir, job_script)
    with open(ref_job) as rj:
        ref_job_contents = rj.read().rstrip()

    assert new_job_contents == ref_job_contents


def test_submit_job_script():
    job_file = 'test.job'
    sub_options = '--mem=32G'
    cluster = 'chimera'

    ec, out = softinstall.submit_job_script(
        job_file, sub_options, cluster=cluster, local_exec=False, dry_run=True
    )

    assert out == ("(DRY RUN) Job submission command: module --force purge && "
                   "module load cluster/chimera && "
                   "sbatch --parsable --mem=32G test.job")
