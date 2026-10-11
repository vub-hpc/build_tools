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
Unit tests for build_tools.lmodtools

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import logging
import os

import pytest

from build_tools import lmodtools
from build_tools.lmodtools import submit_lmod_cache_job


def test_submit_lmod_cache_job(inputdir):
    job_script = 'lmod_cache_job_01.sh'

    _, out = submit_lmod_cache_job('skylake_mpi', jobids_depend=['123', '456'], dry_run=True)

    new_job = out.split(' ')[-1]
    with open(new_job) as nj:
        new_job_contents = nj.read().rstrip()

    ref_job = os.path.join(inputdir, job_script)
    with open(ref_job) as rj:
        ref_job_contents = rj.read().rstrip()

    assert new_job_contents == ref_job_contents


def test_submit_lmod_cache_job_gpu_required(inputdir):
    # sofia zen4_h200 requires at least 1 GPU, otherwise the job gets blocked
    job_script = 'lmod_cache_job_02.sh'

    _, out = submit_lmod_cache_job('zen4_h200', dry_run=True)

    new_job = out.split(' ')[-1]
    with open(new_job) as nj:
        new_job_contents = nj.read().rstrip()

    ref_job = os.path.join(inputdir, job_script)
    with open(ref_job) as rj:
        ref_job_contents = rj.read().rstrip()

    assert new_job_contents == ref_job_contents


def test_submit_lmod_cache_job_spider_cache(inputdir):
    # brussel zen5-ib has lmod_json_spider_cache enabled in the arch definitions
    job_script = 'lmod_cache_job_03.sh'

    _, out = submit_lmod_cache_job('zen5_mpi', dry_run=True)

    new_job = out.split(' ')[-1]
    with open(new_job) as nj:
        new_job_contents = nj.read().rstrip()

    ref_job = os.path.join(inputdir, job_script)
    with open(ref_job) as rj:
        ref_job_contents = rj.read().rstrip()

    assert new_job_contents == ref_job_contents


def test_submit_lmod_cache_job_failure(monkeypatch, caplog):
    monkeypatch.setattr(lmodtools, 'write_tempfile', lambda script: '/tmp/fake_cache_job.sh')
    monkeypatch.setattr(lmodtools, 'submit_job_script', lambda *args, **kwargs: (1, 'fake submission error'))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            submit_lmod_cache_job('zen5_mpi')

    assert exc.value.code == 1
    assert "Failed to submit Lmod cache job: fake submission error" in caplog.text
