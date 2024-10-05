#!/bin/bash -l
#SBATCH --job-name=test-job
#SBATCH --output="%x-%j.out"
#SBATCH --error="%x-%j.err"
#SBATCH --time=23:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --gpus-per-node=0
#SBATCH --partition=skylake_mpi

if [ -z $PREFIX_EB ]; then
  echo 'PREFIX_EB is not set!'
  exit 1
fi

# set environment
export BUILD_TOOLS_LOAD_DUMMY_MODULES=1
export BUILD_TOOLS_RUN_LMOD_CACHE=1
export LANG=C
export PATH=$PREFIX_EB/easybuild-framework:$PATH
export PYTHONPATH=$PREFIX_EB/easybuild-easyconfigs:$PREFIX_EB/easybuild-easyblocks:$PREFIX_EB/easybuild-framework:$PREFIX_EB/vsc-base/lib

# make build directory
if [ -z $SLURM_JOB_ID ]; then
    export TMPDIR=/tmp/eb-test-build/$USER/
fi
mkdir -p $TMPDIR
mkdir -p /tmp/eb-test-build

# update MODULEPATH for cross-compilations
local_arch="$VSC_ARCH_LOCAL$VSC_ARCH_SUFFIX"
if [ "skylake" != "$local_arch" ]; then
    export MODULEPATH=${MODULEPATH//$local_arch/skylake}
fi

 eb 

if [ $? -ne 0 ]; then
    if [ -n "$SLURM_JOB_ID" ]; then
        rm -rf /tmp/eb-test-build
    fi
    exit 1
fi
