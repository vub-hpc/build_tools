#!/bin/bash -l
#SBATCH --job-name=test-job-gpu
#SBATCH --output="%x-%j.out"
#SBATCH --error="%x-%j.err"
#SBATCH --time=23:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --gpus-per-node=1
#SBATCH --partition=ampere_gpu

if [ -z $PREFIX_EB ]; then
  echo 'PREFIX_EB is not set!'
  exit 1
fi

# set environment
export BUILD_TOOLS_LOAD_DUMMY_MODULES=1
export BUILD_TOOLS_RUN_LMOD_CACHE=
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
if [ "zen2" != "$VSC_ARCH_LOCAL" ]; then
    moddir="/apps/brussel/${VSC_OS_LOCAL}/zen2-ib/modules"
    # use modules from target arch and toolchain generation
    CC_MODULEPATH=${moddir}/2020b/all
    # also add last 3 years of modules in case out-of-toolchain deps are needed
    for modpath in $(ls -1dr ${moddir}/*/all | head -n 6); do
        CC_MODULEPATH="$CC_MODULEPATH:$modpath"
    done
    export MODULEPATH=$CC_MODULEPATH
fi

bwrap eb  --cuda-compute-capabilities=8.0

if [ $? -ne 0 ]; then
    if [ -n "$SLURM_JOB_ID" ]; then
        rm -rf /tmp/eb-test-build
    fi
    exit 1
fi

rsync src dest
