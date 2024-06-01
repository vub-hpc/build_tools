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
Unit tests for build_tools.lmodtools

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os

from build_tools.lmodtools import submit_lmod_cache_job

def test_submit_lmod_cache_job(inputdir):
    job_script = 'lmod_cache_job_01.sh'

    _, out = submit_lmod_cache_job(jobids_depend=['123', '456'], partition='skylake_mpi', dry_run=True)

    new_job = out.split(' ')[-1]
    with open(new_job) as nj:
        new_job_contents = nj.read().rstrip()

    ref_job = os.path.join(inputdir, job_script)
    with open(ref_job) as rj:
        ref_job_contents = rj.read().rstrip()

    assert new_job_contents == ref_job_contents
