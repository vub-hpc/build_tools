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
Unit tests for build_tools.filetools

@author: Alex Domingo (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
"""

import logging
import os

import pytest

from build_tools import filetools


def test_write_tempfile():
    contents = "Hello world!"
    tmp_file = filetools.write_tempfile(contents)

    try:
        with open(tmp_file) as tf:
            tmp_file_contents = tf.read()

        assert tmp_file_contents == contents
    finally:
        os.unlink(tmp_file)


@pytest.fixture
def fetch_lock_config(monkeypatch, tmp_path):
    """stub out the EasyBuild accessors used by the fetch lock"""
    monkeypatch.setattr(filetools, 'source_paths', lambda: [str(tmp_path)])
    monkeypatch.setattr(filetools, 'mkdir', lambda path, **kwargs: os.makedirs(path, exist_ok=True))


def test_acquire_fetch_lock(tmp_path, fetch_lock_config):
    log = logging.getLogger('test_filetools')

    lock = filetools.acquire_fetch_lock('zlib', log)

    lock_name = f'{tmp_path}/z/zlib'.replace('/', '_') + '.lock'
    assert (tmp_path / '.locks' / lock_name).is_file()
    assert lock.lockfile == str(tmp_path / '.locks' / lock_name)


def test_release_fetch_lock(tmp_path, caplog, fetch_lock_config):
    log = logging.getLogger('test_filetools')

    lock = filetools.acquire_fetch_lock('zlib', log)
    filetools.release_fetch_lock(lock, log)

    assert not (tmp_path / '.locks' / lock.lockfile.split('/.locks/')[1]).is_file()

    # releasing an already released lock only logs a warning
    with caplog.at_level(logging.WARNING):
        filetools.release_fetch_lock(lock, log)
    assert 'was already released' in caplog.text


def test_acquire_fetch_lock_waits(monkeypatch, tmp_path, fetch_lock_config):
    sleeps = []
    monkeypatch.setattr(filetools.time, 'sleep', sleeps.append)
    attempts = []

    class FakeLock:
        def __init__(self, lockfile, **kwargs):
            self.lockfile = lockfile

        @property
        def state(self):
            return filetools.LockState.unknown

        def lock(self):
            attempts.append(1)
            if len(attempts) <= 2:
                raise filetools.TimeOutError('held')

    monkeypatch.setattr(filetools, 'Lock', FakeLock)

    filetools.acquire_fetch_lock('zlib', logging.getLogger('test_filetools'))

    assert len(attempts) == 3
    assert sleeps == [60, 60]


def test_acquire_fetch_lock_timeout(monkeypatch, tmp_path, fetch_lock_config):
    monkeypatch.setattr(filetools.time, 'sleep', lambda s: None)

    class FakeLock:
        def __init__(self, lockfile, **kwargs):
            self.lockfile = lockfile

        @property
        def state(self):
            return filetools.LockState.unknown

        def lock(self):
            raise filetools.TimeOutError('held')

    monkeypatch.setattr(filetools, 'Lock', FakeLock)

    with pytest.raises(filetools.EasyBuildError, match='Maximum wait time'):
        filetools.acquire_fetch_lock('zlib', logging.getLogger('test_filetools'))


class FakeStaleLock:
    """Lock stand-in that simulates a lock left behind by a killed build"""

    def __init__(self, lockfile, **kwargs):
        self.lockfile = lockfile

    @property
    def state(self):
        return filetools.LockState.stale if os.path.exists(self.lockfile) else filetools.LockState.unlocked

    def lock(self):
        if os.path.exists(self.lockfile):
            raise filetools.TimeOutError('held')

    def unlock(self):
        pass


def test_acquire_fetch_lock_stale(tmp_path, monkeypatch, fetch_lock_config, caplog):
    # leave a lock behind, as a killed build would
    lockfile = tmp_path / '.locks' / (f'{tmp_path}/z/zlib'.replace('/', '_') + '.lock')
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text(f'{lockfile}|localhost|1234|random')
    monkeypatch.setattr(filetools, 'Lock', FakeStaleLock)
    log = logging.getLogger('test_filetools')

    with caplog.at_level(logging.INFO):
        filetools.acquire_fetch_lock('zlib', log)

    assert not lockfile.is_file()
    assert 'is stale' in caplog.text


def test_acquire_fetch_lock_stale_already_broken(tmp_path, monkeypatch, fetch_lock_config):
    # another build breaks the stale lock between the state check and the removal
    lockfile = tmp_path / '.locks' / (f'{tmp_path}/z/zlib'.replace('/', '_') + '.lock')
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text(f'{lockfile}|localhost|1234|random')
    monkeypatch.setattr(filetools, 'Lock', FakeStaleLock)
    removed = []
    real_remove = os.remove

    def fake_remove(path):
        if not removed:
            removed.append(path)
            raise FileNotFoundError(path)
        real_remove(path)

    monkeypatch.setattr(filetools.os, 'remove', fake_remove)

    filetools.acquire_fetch_lock('zlib', logging.getLogger('test_filetools'))

    assert len(removed) == 1
    assert not lockfile.is_file()


def test_write_tempfile_ioerror(monkeypatch, caplog):
    def fake_named_tempfile(*args, **kwargs):
        raise IOError("fake IO error")

    monkeypatch.setattr(filetools.tempfile, 'NamedTemporaryFile', fake_named_tempfile)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            filetools.write_tempfile("Hello world!")

    assert exc.value.code == 1
    assert "Error writing tmp file" in caplog.text
