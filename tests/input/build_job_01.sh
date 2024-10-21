#!/bin/bash -l
#SBATCH --job-name=test-job
#SBATCH --output="%x-%j.out"
#SBATCH --error="%x-%j.err"
#SBATCH --time=23:59:59
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --gpus-per-node=0
#SBATCH --partition=skylake_mpi

test -n "$PREFIX_EB" || { echo "ERROR: environment variable PREFIX_EB not set"; exit 1; }

# set environment
export BUILD_TOOLS_LOAD_DUMMY_MODULES=1
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

EB='eb'

if [ "0" == 1 ]; then
    echo "BUILD_TOOLS: installing with bwrap"
    output=$(EASYBUILD_ROBOT_PATHS=/some/path get_module_from_easyconfig.py zlib-1.2.11.eb) || { echo "ERROR: get_module_from_easyconfig.py failed"; exit 1; }
    echo "BUILD_TOOLS: get_module_from_easyconfig.py output: $output"
    while read -r key value; do
        [ "$key" == "==" ] && continue
        [ "$key" == "modname" ] && modname="$value"
        [ "$key" == "modversion" ] && modversion="$value"
    done <<< "$output"
    echo "BUILD_TOOLS: modname $modname modversion $modversion"
    [[ -n $modname && -n $modversion ]] || { echo "ERROR: failed to get modname and/or modversion"; exit 1; }
    appsmnt="/vscmnt/brussel_pixiu_apps/_apps_brussel"
    softbwrap="/apps/brussel/bwrap/$VSC_OS_LOCAL/skylake/software/$modname"
    softreal="$appsmnt/$VSC_OS_LOCAL/skylake/software/$modname"
    modbwrap="/apps/brussel/$VSC_OS_LOCAL/skylake/.modules_bwrap/all/$modname"
    mkdir -p "$softbwrap"
    mkdir -p "$modbwrap"
    bwrap_cmd=(
        bwrap
        --bind / /
        --bind "$softbwrap" "$softreal"
        --dev /dev
        --bind /dev/log /dev/log
    )
    EB="${bwrap_cmd[*]} $EB"
    echo "BUILD_TOOLS: bwrap eb command: $EB"
fi

eb_stderr=$(mktemp).eb_stderr
$EB zlib-1.2.11.eb  2>"$eb_stderr"

ec=$?
cat "$eb_stderr" >>/dev/stderr

if [ $ec -ne 0 ]; then
    echo "BUILD_TOOLS: EasyBuild exited with non-zero exit code ($ec)" >>/dev/stderr
    if [ -n "$SLURM_JOB_ID" ]; then
        rm -rf /tmp/eb-test-build
    fi
    exit $ec
fi

if [ "0" == 1 ]; then
    dest_modfile=$(grep "^BUILD_TOOLS: real_mod_filepath" "$eb_stderr" | cut -d " " -f 3) || { echo "ERROR: failed to obtain destination module file path"; exit 1; }
    source_installdir="$softbwrap/$modversion/"
    dest_installdir="$softreal/$modversion/"
    source_modfile="$modbwrap/$modversion.lua"
    echo "BUILD_TOOLS: source/destination install dir: $source_installdir $dest_installdir"
    echo "BUILD_TOOLS: source/destination module file: $source_modfile $dest_modfile"
    test -d "$source_installdir" || { echo "ERROR: source install dir does not exist"; exit 1; }
    test -n "$(ls -A $source_installdir)" || { echo "ERROR: source install dir is empty"; exit 1; }
    test -s "$source_modfile" || { echo "ERROR: source module file does not exist or is empty"; exit 1; }
    rsync -a --link-dest="$source_installdir" "$source_installdir" "$dest_installdir" || { echo "ERROR: failed to copy install dir"; exit 1; }
    rsync -a --link-dest="$modbwrap" "$source_modfile" "$dest_modfile" || { echo "ERROR: failed to copy module file"; exit 1; }
    rm -rf "$source_installdir" "$source_modfile"
    echo "BUILD_TOOLS: installation moved from bwrap to real location"
fi

builds_succeeded=$(grep "^BUILD_TOOLS: builds_succeeded" "$eb_stderr")
if [[ "1" == 1 && -n "${builds_succeeded}" ]];then
    job_options=(
        --wait
        --time=1:0:0
        --mem=1g
        --output=%x_%j.log
        --job-name=lmod_cache_skylake
        --dependency=singleton
        --partition=skylake_mpi
    )
    cmd=(
        /usr/libexec/lmod/run_lmod_cache.py
        --create-cache
        --architecture skylake
        --module-basedir /apps/brussel/$VSC_OS_LOCAL
    )
    echo "BUILD_TOOLS: submitting Lmod cache update job on partition skylake_mpi for architecture skylake"
    sbatch "${job_options[@]}" --wrap "${cmd[*]}"
fi
