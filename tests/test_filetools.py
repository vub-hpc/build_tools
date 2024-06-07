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
Unit tests for build_tools.filetools

@author: Alex Domingo (Vrije Universiteit Brussel)
author: Samuel Moors (Vrije Universiteit Brussel)
"""

import os
import shutil

from build_tools import filetools

MODULERC = """-- VERSION SWAPS FOR IB MODULES
local arch_suffix=os.getenv("VSC_ARCH_SUFFIX") or ""
if ( arch_suffix == "-ib") then
    module_version("OpenMPI/4.1.1-GCC-10.3.0-ib", "4.1.1-GCC-10.3.0")
    module_version("OpenMPI/4.0.5-GCC-10.2.0-ib", "4.0.5-GCC-10.2.0")
end
-- END OF VERSION SWAPS FOR IB MODULES"""


def test_write_tempfile():
    contents = "Hello world!"
    tmp_file = filetools.write_tempfile(contents)

    with open(tmp_file) as tf:
        tmp_file_contents = tf.read()

    assert tmp_file_contents == contents


def test_clean_append_new(tmpdir):
    modrc_path = os.path.join(tmpdir.strpath, '.modulerc.lua')
    filetools.clean_append(modrc_path, MODULERC)

    with open(modrc_path, 'r') as mf:
        modrc_text = mf.read()

    assert modrc_text == MODULERC


def test_clean_append_old(inputdir, tmpdir):
    old_modulerc = os.path.join(inputdir, 'modulerc_01.lua')
    modrc_path = os.path.join(tmpdir.strpath, '.modulerc.lua')

    shutil.copyfile(old_modulerc, modrc_path)
    filetools.clean_append(modrc_path, MODULERC)

    with open(modrc_path, 'r') as mf:
        modrc_text = mf.read()

    ref_modrc_text = """-- default version of Java 1.8
module_version("Java/1.8.0_281", "1.8")

-- hide all GCC v4.x
hide_version("GCCcore/4")
%s""" % MODULERC

    assert modrc_text == ref_modrc_text


def test_get_module(inputdir, get_module_cmd):
    easyconfig = os.path.join(inputdir, 'zlib-1.2.11.eb')
    _, module = filetools.get_module(easyconfig, cmd=get_module_cmd)

    assert module[0] == 'zlib'
    assert module[1] == '1.2.11'
