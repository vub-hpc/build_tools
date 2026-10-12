#!/bin/bash
#SBATCH --time=1:0:0
#SBATCH --output=%x_%j.log
#SBATCH --job-name=lmod_cache_zen5-ib
#SBATCH --dependency=singleton,afterok:123:456
#SBATCH --partition=zen5_mpi
/usr/libexec/lmod/run_lmod_cache.py --create-cache --architecture zen5-ib --module-basedir /apps/brussel/${VSC_OS_LOCAL:?} --create-spider-cache
