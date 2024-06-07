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
Unit tests for build_tools.bwraptools

@author: Samuel Moors (Vrije Universiteit Brussel)
"""

from build_tools import bwraptools

job_options = {
    'eb_installpath': '/apps/brussel/$VSC_OS_LOCAL/skylake',
    'tc_gen': '2022a',
}


def test_bwrap_prefix(mock_realpath_apps_brussel):
    prefix = bwraptools.bwrap_prefix(job_options, 'HPL', 'skylake')
    ref_prefix = 'mkdir -p /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL && mkdir -p /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL && bwrap --bind / / --bind /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL /vscmnt/brussel_pixiu_apps/_apps_brussel/$VSC_OS_LOCAL/skylake/software/HPL --bind /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL /vscmnt/brussel_pixiu_apps/_apps_brussel/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL --dev /dev --bind /dev/log /dev/log'  # noqa: E501

    assert prefix == ref_prefix


def test_rsync_copy():
    rsync_cmds = bwraptools.rsync_copy(job_options, 'HPL', '2.3-foss-2022a', 'skylake')
    ref_rsync_cmds = """\
echo "bwrap install dir: /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/"
echo "destination install dir: /apps/brussel/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/"
echo "bwrap module file: /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua"
echo "destination module file: /apps/brussel/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua"
if [ ! -d /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/ ]; then echo "ERROR: bwrap install dir does not exist"; exit 1; fi
if [ ! "$(ls -A /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/)" ]; then echo "ERROR: bwrap install dir empty"; exit 1; fi
if [ ! -s /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua ]; then echo "ERROR: bwrap module file does not exist or empty"; exit 1; fi
rsync -a --link-dest=/apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/ /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/ /apps/brussel/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/
if [ $? -ne 0 ]; then echo "ERROR: failed to copy bwrap install dir"; exit 1; fi
rsync -a --link-dest=/apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua /apps/brussel/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua
if [ $? -ne 0 ]; then echo "ERROR: failed to copy bwrap module file"; exit 1; fi
rm -rf /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/HPL/2.3-foss-2022a/ /apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/modules/2022a/all/HPL/2.3-foss-2022a.lua"""  # noqa: E501

    assert rsync_cmds == ref_rsync_cmds
