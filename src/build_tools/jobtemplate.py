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

BUILD_JOB = """\
#!/bin/bash -l
#SBATCH --job-name=${job_name}
#SBATCH --output="%x-%j.out"
#SBATCH --error="%x-%j.err"
#SBATCH --time=${walltime}
#SBATCH --nodes=${nodes}
#SBATCH --ntasks=${tasks}
#SBATCH --gpus-per-node=${gpus}
#SBATCH --partition=${partition}

# activate build_tools virtual environment
source "$$VSC_SCRATCH_VO_USER/EB5/eb5env/bin/activate"

# set environment
export BUILD_TOOLS_LOAD_DUMMY_MODULES=1
export LANG=${langcode}
export MODULEPATH=""  # EB prepends 'modules/collection' to MODULEPATH

SUBDIR_MODULES="modules"
SUBDIR_MODULES_BWRAP=".modules_bwrap"
SUFFIX_MODULES_PATH="collection"
SUFFIX_MODULES_SYMLINK="all"

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

EB='eb'

if [ "${bwrap}" == 1 ]; then
    echo "BUILD_TOOLS: installing with bwrap"
    output=$$(EASYBUILD_ROBOT_PATHS=${robot_paths} EASYBUILD_IGNORE_INDEX=1 ec2ml.py ${easyconfig}) || { echo "ERROR: ec2ml.py failed"; exit 1; }
    echo "BUILD_TOOLS: ec2ml.py ${easyconfig} output: $$output"
    while read -r key value; do
        [ "$$key" == "full_mod_name" ] && { modname=$${value%/*}; modversion=$${value#*/}; break; }
    done <<< "$$output"
    echo "BUILD_TOOLS: modname $$modname modversion $$modversion"
    [[ -n $$modname && -n $$modversion ]] || { echo "ERROR: failed to get modname and/or modversion"; exit 1; }
    appsmnt="/vscmnt/brussel_pixiu_apps/_apps_brussel"
    softbwrap="/apps/brussel/bwrap/$$VSC_OS_LOCAL/${target_arch}/software/$$modname"
    softreal="$$appsmnt/$$VSC_OS_LOCAL/${target_arch}/software/$$modname"
    mkdir -p "$$softbwrap"
    bwrap_cmd=(
        bwrap
        --bind / /
        --bind "$$softbwrap" "$$softreal"
        --dev /dev
        --bind /dev/log /dev/log
    )
    EB="$${bwrap_cmd[*]} $$EB"
    echo "BUILD_TOOLS: bwrap eb command: $$EB"
fi

eb_stderr=$$(mktemp).eb_stderr
$$EB ${easyconfig} ${eb_options} 2>"$$eb_stderr"

ec=$$?
cat "$$eb_stderr" >>/dev/stderr

if [ $$ec -ne 0 ]; then
    echo "BUILD_TOOLS: EasyBuild exited with non-zero exit code ($$ec)" >>/dev/stderr
    if [ -n "$$SLURM_JOB_ID" ]; then
        rm -rf ${eb_buildpath}
    fi
    exit $$ec
fi

if [ "${bwrap}" == 1 ]; then
    source_installdir="$$softbwrap/$$modversion/"
    dest_installdir="$$softreal/$$modversion/"
    installbase="/apps/brussel/$$VSC_OS_LOCAL/${target_arch}"
    source_modfile="$$installbase/$$SUBDIR_MODULES_BWRAP/$$SUFFIX_MODULES_PATH/$$modname/$$modversion.lua"
    source_modsymlink=$$(echo $$installbase/$$SUBDIR_MODULES_BWRAP/*/$$SUFFIX_MODULES_SYMLINK/$$modname/$$modversion.lua)
    dest_modfile="$$installbase/$$SUBDIR_MODULES/$$SUFFIX_MODULES_PATH/$$modname/$$modversion.lua"
    dest_modsymlink=$${source_modsymlink/$$installbase\/$$SUBDIR_MODULES_BWRAP\//$$installbase\/$$SUBDIR_MODULES\/}
    echo "BUILD_TOOLS: source/dest install dir: $$source_installdir $$dest_installdir"
    echo "BUILD_TOOLS: source/dest module file: $$source_modfile $$dest_modfile"
    echo "BUILD_TOOLS: source/dest module symlink: $$source_modsymlink $$dest_modsymlink"
    test -d "$$source_installdir" || { echo "ERROR: source install dir does not exist"; exit 1; }
    test -n "$$(ls -A $$source_installdir)" || { echo "ERROR: source install dir is empty"; exit 1; }
    test -s "$$source_modfile" || { echo "ERROR: source module file does not exist or is empty"; exit 1; }
    test $$(readlink "$$source_modsymlink") == "$$source_modfile" || { echo "ERROR: source module symlink does not link to correct file"; exit 1; }
    mkdir -p $$(dirname "$$dest_modfile") $$(dirname "$$dest_modsymlink")
    tempfile=$$(mktemp -p /tmp)
    rsync -a --link-dest="$$source_installdir" "$$source_installdir" "$$dest_installdir" || { echo "ERROR: failed to copy install dir"; exit 1; }
    cp -p "$$source_modfile" "$$dest_modfile"
    ln -sf "$$dest_modfile" "$$tempfile"
    mv -f "$$tempfile" "$$dest_modsymlink"
    test $$(readlink "$$dest_modsymlink") == "$$dest_modfile" || { echo "ERROR: failed to create symlink to module file"; exit 1; }
    rm -rf "$$source_installdir" "$$source_modfile" "$$source_modsymlink"
    echo "BUILD_TOOLS: installation moved from bwrap to real location"
fi

builds_succeeded=$$(grep "^BUILD_TOOLS: builds_succeeded" "$$eb_stderr")
if [[ "${lmod_cache}" == 1 && -n "$${builds_succeeded}" ]];then
    job_options=(
        --wait
        --time=1:0:0
        --mem=1g
        --output=%x_%j.log
        --job-name=lmod_cache_${target_arch}
        --dependency=singleton
        --partition=${partition}
    )
    cmd=(
        /usr/libexec/lmod/run_lmod_cache.py
        --create-cache
        --architecture ${target_arch}
        --module-basedir /apps/brussel/$$VSC_OS_LOCAL
    )
    echo "BUILD_TOOLS: submitting Lmod cache update job on partition ${partition} for architecture ${target_arch}"
    sbatch "$${job_options[@]}" --wrap "$${cmd[*]}"
fi

"""  # noqa

BuildJob = Template(BUILD_JOB)
