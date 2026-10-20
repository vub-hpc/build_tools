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
Unit tests for build_tools.softinstall

@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import logging
import os

import pytest

from build_tools import softinstall


@pytest.mark.parametrize(
    'test_name',
    [
        (
            'zlib-1.2.11',
            ['zlib-1.2.11.eb', None]
        ),
        (
            'zlib-1.2.11-zen5-ib',
            ['zlib-1.2.11.eb', 'zen5-ib']
        ),
        (
            'zlib-1.2.11-zen5-ib',
            ['test/subdir/zlib-1.2.11.eb', 'zen5-ib'],
        ),
        (
            'zlib-1.2.11-ngzip-2.3.3',
            ['zlib-1.2.11.eb ngzip-2.3.3.eb', None]
        ),
        (
            'zlib-1.2.11-ngzip-2.3.3-zen5-ib',
            ['zlib-1.2.11.eb test/subdir/ngzip-2.3.3.eb', 'zen5-ib'],
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
            'appsmnt': '/vscmnt/brussel_pixiu_apps/_apps_brussel',
            'bwrap': '0',
            'easyconfig': 'zlib-1.2.11.eb',
            'eb_buildpath': '/tmp/eb-test-build',
            'eb_options': '',
            'gpus': '',
            'job_name': 'test-job',
            'langcode': 'C',
            'machine': 'brussel',
            'nodes': 1,
            'partition': 'zen5_mpi',
            'robot_paths': '/some/path',
            'host_arch': 'zen5-ib',
            'tasks': 4,
            'tmp': '/tmp/eb-test-build',
            'venv_activate': '$HOME/EB5/eb5env/bin/activate',
            'walltime': '23:59:59',
        }),
        ('build_job_02.sh', {
            'appsmnt': '/vscmnt/brussel_pixiu_apps/_apps_brussel',
            'bwrap': 1,
            'easyconfig': 'zlib-1.2.11.eb',
            'eb_buildpath': '/tmp/eb-test-build',
            'eb_options': '--cuda-compute-capabilities=8.0',
            'gpus': '--gpus-per-node=1',
            'job_name': 'test-job-gpu',
            'langcode': 'C',
            'machine': 'brussel',
            'nodes': 1,
            'partition': 'ampere_gpu',
            'robot_paths': '/some/path',
            'host_arch': 'zen2-ib',
            'tasks': 4,
            'tmp': '/tmp/eb-test-build',
            'venv_activate': '$HOME/EB5/eb5env/bin/activate',
            'walltime': '23:59:59',
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

    assert out == ("(DRY RUN) Job submission command: "
                   "sbatch -M chimera --parsable --mem=32G test.job")


def test_submit_job_script_quoted_options():
    job_file = 'test.job'
    sub_options = '--mem=32G --comment="my job"'

    ec, out = softinstall.submit_job_script(
        job_file, sub_options, cluster=None, local_exec=False, dry_run=True
    )

    assert out == ("(DRY RUN) Job submission command: "
                   "sbatch --parsable --mem=32G '--comment=my job' test.job")


def test_run_no_shell():
    ec, out = softinstall.run_no_shell("echo hello")

    assert ec == 0
    assert out == "hello\n"

    ec, out = softinstall.run_no_shell("false")

    assert ec != 0


def test_run_loop_stdout(capsys):
    ec, out = softinstall.run_loop_stdout("bash -c 'echo line1; echo line2'")

    assert ec == 0
    assert out == "line1\nline2\n"

    # the output must also be written to stdout as it is produced
    captured = capsys.readouterr()
    assert "line1" in captured.out
    assert "line2" in captured.out


def test_submit_job_script_local_exec(tmp_path):
    job_file = tmp_path / 'test.job'
    job_file.write_text("#!/bin/bash\necho local-run\n")

    ec, out = softinstall.submit_job_script(str(job_file), local_exec=True)

    assert ec == 0
    assert "local-run" in out


def test_submit_job_script_sbatch(monkeypatch):
    submitted = []

    def fake_run_no_shell(cmd):
        submitted.append(cmd)
        return 0, '12345'

    monkeypatch.setattr(softinstall, 'run_no_shell', fake_run_no_shell)

    ec, out = softinstall.submit_job_script('test.job', sub_options='--mem=32G', cluster='chimera')

    assert ec == 0
    assert out == '12345'
    assert len(submitted) == 1
    assert submitted[0] == 'bash -c "sbatch -M chimera --parsable --mem=32G test.job"'


def test_submit_build_job_removes_job_file(monkeypatch, caplog):
    job_options = {
        'appsmnt': '/vscmnt/brussel_pixiu_apps/_apps_brussel',
        'bwrap': '0',
        'easyconfig': 'zlib-1.2.11.eb',
        'eb_buildpath': '/tmp/eb-test-build',
        'eb_options': '',
        'gpus': '',
        'job_name': 'test-job',
        'langcode': 'C',
        'lmod_cache': '1',
        'lmod_cache_cmd': (
            '/usr/libexec/lmod/run_lmod_cache.py --create-cache --architecture zen5-ib '
            '--module-basedir /apps/brussel/${VSC_OS_LOCAL:?} && '
            '/usr/libexec/lmod/run_lmod_cache.py --architecture zen5-ib '
            '--module-basedir /apps/brussel/${VSC_OS_LOCAL:?} --create-spider-cache --cluster-name hydra && '
            '/usr/libexec/lmod/run_lmod_cache.py --architecture zen5-ib '
            '--module-basedir /apps/brussel/${VSC_OS_LOCAL:?} --create-spider-cache --cluster-name anansi'
        ),
        'machine': 'brussel',
        'nodes': 1,
        'partition': 'zen5_mpi',
        'robot_paths': '/some/path',
        'host_arch': 'zen5-ib',
        'tasks': 4,
        'tmp': '/tmp/eb-test-build',
        'venv_activate': '$HOME/EB5/eb5env/bin/activate',
        'walltime': '23:59:59',
    }

    # with keep_job=False the job script file is removed after submission
    ec, out = softinstall.submit_build_job(
        job_options, keep_job=False, sub_options='', cluster='hydra', local_exec=False, dry_run=True
    )

    assert ec == 0
    job_file = out.split(' ')[-1]
    assert not os.path.exists(job_file)

    # an error removing the job file is logged, not raised
    def fake_remove(path):
        raise IOError("fake remove error")

    monkeypatch.setattr(softinstall.os, 'remove', fake_remove)

    with caplog.at_level(logging.ERROR):
        ec, out = softinstall.submit_build_job(
            job_options, keep_job=False, sub_options='', cluster='hydra', local_exec=False, dry_run=True
        )

    assert ec == 0
    assert "Failed to remove job file" in caplog.text
