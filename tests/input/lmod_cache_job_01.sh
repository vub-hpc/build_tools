#!/bin/bash
#SBATCH --time=1:0:0
#SBATCH --mem=1g
#SBATCH --output=%x_%j.log
#SBATCH --job-name=lmod_cache_skylake-ib
#SBATCH --dependency=singleton,afterok:123:456
#SBATCH --partition=skylake_mpi
/usr/libexec/lmod/run_lmod_cache.py --create-cache --architecture skylake-ib --module-basedir /apps/brussel/$VSC_OS_LOCAL
