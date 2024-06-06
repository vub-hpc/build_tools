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
if [ "${target_arch}" != "$$VSC_ARCH_LOCAL" ]; then
    moddir="${eb_installpath}/modules"
    # use modules from target arch and toolchain generation
    CC_MODULEPATH=$${moddir}/${tc_gen}/all
    # also add last 3 years of modules in case out-of-toolchain deps are needed
    for modpath in $$(ls -1dr $${moddir}/*/all | head -n 6); do
        CC_MODULEPATH="$$CC_MODULEPATH:$$modpath"
    done
    export MODULEPATH=$$CC_MODULEPATH
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
