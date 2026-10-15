#!/bin/bash
#SBATCH --time=1:0:0
#SBATCH --output=%x_%j.log
#SBATCH --job-name=lmod_cache_zen4-ib
#SBATCH --dependency=singleton
#SBATCH --partition=zen4_h200
#SBATCH --gpus-per-node=1
/usr/libexec/lmod/run_lmod_cache.py --create-cache --architecture zen4-ib --module-basedir /apps/sofia/${VSC_OS_LOCAL:?}
