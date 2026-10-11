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


def test_write_tempfile_ioerror(monkeypatch, caplog):
    def fake_named_tempfile(*args, **kwargs):
        raise IOError("fake IO error")

    monkeypatch.setattr(filetools.tempfile, 'NamedTemporaryFile', fake_named_tempfile)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            filetools.write_tempfile("Hello world!")

    assert exc.value.code == 1
    assert "Error writing tmp file" in caplog.text
