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
Job template to submit build jobs

@author: Ward Poelmans (Vrije Universiteit Brussel)
@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

from string import Template

BUILD_JOB = """#!/bin/bash -l
#SBATCH --job-name=${job_name}
#SBATCH --output="%x-%j.out"
#SBATCH --error="%x-%j.err"
#SBATCH --time=${walltime}
#SBATCH --nodes=${nodes}
#SBATCH --ntasks=${tasks}
#SBATCH --gpus-per-node=${gpus}
#SBATCH --partition=${partition}

if [ -z $$PREFIX_EB ]; then
  echo 'PREFIX_EB is not set!'
  exit 1
fi

# set environment
export BUILD_TOOLS_LOAD_DUMMY_MODULES=1
export BUILD_TOOLS_RUN_LMOD_CACHE=${lmod_cache}
export LANG=${langcode}
export PATH=$$PREFIX_EB/easybuild-framework:$$PATH
export PYTHONPATH=$$PREFIX_EB/easybuild-easyconfigs:$$PREFIX_EB/easybuild-easyblocks:$$PREFIX_EB/easybuild-framework:$$PREFIX_EB/vsc-base/lib

# make build directory
if [ -z $$SLURM_JOB_ID ]; then
    export TMPDIR=${tmp}/$$USER/
fi
mkdir -p $$TMPDIR
mkdir -p ${eb_buildpath}

# update MODULEPATH for cross-compilations
local_arch="$$VSC_ARCH_LOCAL$$VSC_ARCH_SUFFIX"
if [ "${target_arch}" != "$$local_arch" ]; then
    export MODULEPATH=$${MODULEPATH//$$local_arch/${target_arch}}
fi

${pre_eb_options} eb ${eb_options}

if [ $$? -ne 0 ]; then
    if [ -n "$$SLURM_JOB_ID" ]; then
        rm -rf ${eb_buildpath}
    fi
    exit 1
fi

${postinstall}

"""  # noqa

BuildJob = Template(BUILD_JOB)
