# build_tools

Tools to build and install software for VUB-HPC

## Installation

Install the EasyBuild dependencies in editable mode and make sure that you use
the main branch of each repo. `pip` only knows about stable releases.
Therefore, if you install a development version, it will **not** fulfill the
version requirements in `pip`. This is not a big issue, because by installing
in editable mode, we can make any changes to the code later on.

### Newer versions of setuptools
Newer versions of `setuptools` have changed the behaviour of editable
installations and that breaks EasyBuild. In such cases, make sure to enable
`compat` mode for the editable installation:

```
pip install -e . --config-settings editable_mode=compat
```
See https://github.com/easybuilders/easybuild-framework/issues/4451

### Virtual environment

```bash
python -m venv /path/to/venv/hpcbuild
source /path/to/venv/hpcbuild/bin/activate
# Install EasyBuild
cd /path/to/easybuild-framework/
python -m pip install --editable . --config-settings editable_mode=compat
cd /path/to/easybuild-easyblocks/
python -m pip install --editable . --config-settings editable_mode=compat
cd /path/to/easybuild-easyconfigs/
python -m pip install --editable . --config-settings editable_mode=compat
# Install other dependencies
# pyyaml is required for parsing easystack files
python -m pip install flufl.lock pytest pyyaml
# Install build_tools
cd /path/to/build_tools/
python -m pip install . --no-deps
```

### Install instructions for sofia

```bash
# install + activate venv
mkdir ~/EB5
python3 -m venv ~/EB5/eb5env
source ~/EB5/eb5env/bin/activate

# install deps
python -m pip install --upgrade pip
python -m pip install wheel
python -m pip install flufl.lock
python -m pip install pyyaml
python -m pip install archspec  # required for BLIS-1.1 in zen5

# clone repos
git clone https://github.com/vub-hpc/build_tools.git ~/EB5/build_tools
git clone https://github.com/easybuilders/easybuild-easyconfigs.git ~/EB5/easybuild-easyconfigs
git clone https://github.com/easybuilders/easybuild-easyblocks.git ~/EB5/easybuild-easyblocks
git clone https://github.com/easybuilders/easybuild-framework.git ~/EB5/easybuild-framework
git clone --single-branch -b site-vub https://github.com/vscentrum/vsc-software-stack.git ~/EB5/vsc-software-stack/site-vub

# add extra python paths for the cloned easybuild repos
cat <<EOF >~/EB5/eb5env/lib/python3.9/site-packages/extra_paths.pth
$HOME/EB5/easybuild-easyconfigs
$HOME/EB5/easybuild-easyblocks
$HOME/EB5/easybuild-framework
EOF

# create symlink to the `eb` executable
ln -sr ~/EB5/easybuild-framework/eb ~/EB5/eb5env/bin/eb

# create symlink to default EB easyconfigs so it's added to the EB robot paths
ln -sr ~/EB5/easybuild-easyconfigs/easybuild/easyconfigs/ ~/EB5/vsc-software-stack/easybuild

# install/update build_tools
git -C ~/EB5/vsc-software-stack/site-vub pull
python -m pip install ~/EB5/build_tools --no-deps --upgrade
```
### Testing

Tests can be carried out with `pytest`:

```bash
cd build_tools
python -m pytest
```

## GPU job submission

`submit_build.py` decides per architecture whether a job is submitted to a
GPU partition or to a regular CPU partition, and whether the job requests
a GPU device (the `gpus` job option of the partition). This is controlled
with the `--gpu` option:

* `--gpu detect` (default): an easyconfig is considered GPU software when
  its filename contains a GPU component or toolchain name (`CUDA`,
  `nvidia-compilers`, `NVHPC`). Jobs for GPU software are submitted to the
  GPU partitions of the architectures that have them, with the partition's
  `gpus` job option; other software and architectures without a GPU
  partition use the regular CPU partitions.
* `--gpu detect-nodevice`: same detection, but the `gpus` job option is
  not added to the job file (exception: partitions with
  `gpu_required: true`): the jobs run either on CPU partitions or on
  GPU partitions.
* `--gpu force`: the detection of GPU software is disabled and all jobs
  are submitted to the GPU partitions of the architectures that have them,
  with the partition's `gpus` job option; architectures without a GPU
  partition use their regular CPU partition.
* `--gpu force-nodevice`: same as `--gpu force`, but the `gpus` job
  option is not added to the job file (exception: partitions with
  `gpu_required: true`).

An explicitly given `--partition` always overrides this behaviour.

Without an explicit `--partition`, `detect*` submits GPU software to the
GPU partition of the architecture and all other software to its CPU
partition, while `force*` submits all software to the GPU partition (or
to the CPU partition when the architecture has no GPU partition).

Architectures come in three flavours, which give different results for
the same combination of options:

* CPU-only architectures: the `gpu` partition is `None`, for example
  `zen3`, `zen3-ib` and `zen4` on brussel.
* GPU-only architectures: the `cpu` and `gpu` partitions are the same
  partition, for example `broadwell` and `zen2-ib` on brussel and
  `zen5-ib` and `zen4-ib` on sofia.
* CPU/GPU architectures: the `cpu` and `gpu` partitions are different,
  for example `zen5-ib` on brussel.

The tables below show, for every combination of easyconfig type, `--gpu`
option and GPU required state, the partition type the job is submitted
to and whether it gets the partition's `gpus` option (i.e. a GPU
device). The GPU required state shown is that of the partition the job
is submitted to. CPU partitions do not define a `gpus` option, so jobs
on them never request a GPU device.

### CPU-only architectures

Architectures with a CPU partition but no GPU partition.

| easyconfig       | `--gpu` option    | GPU required | Partition result | GPU device |
|------------------|-------------------|--------------|------------------|------------|
| non-GPU software | `detect`          | false        | cpu              | no         |
| non-GPU software | `detect`          | true         | cpu              | no         |
| non-GPU software | `detect-nodevice` | false        | cpu              | no         |
| non-GPU software | `detect-nodevice` | true         | cpu              | no         |
| non-GPU software | `force`           | false        | cpu              | no         |
| non-GPU software | `force`           | true         | cpu              | no         |
| non-GPU software | `force-nodevice`  | false        | cpu              | no         |
| non-GPU software | `force-nodevice`  | true         | cpu              | no         |
| GPU software     | `detect`          | false        | cpu              | no         |
| GPU software     | `detect`          | true         | cpu              | no         |
| GPU software     | `detect-nodevice` | false        | cpu              | no         |
| GPU software     | `detect-nodevice` | true         | cpu              | no         |
| GPU software     | `force`           | false        | cpu              | no         |
| GPU software     | `force`           | true         | cpu              | no         |
| GPU software     | `force-nodevice`  | false        | cpu              | no         |
| GPU software     | `force-nodevice`  | true         | cpu              | no         |

### GPU-only architectures

Architectures with a GPU partition as CPU partition.

| easyconfig       | `--gpu` option    | GPU required | Partition result | GPU device |
|------------------|-------------------|--------------|------------------|------------|
| non-GPU software | `detect`          | false        | cpu (same as gpu)| no         |
| non-GPU software | `detect`          | true         | cpu (same as gpu)| yes        |
| non-GPU software | `detect-nodevice` | false        | cpu (same as gpu)| no         |
| non-GPU software | `detect-nodevice` | true         | cpu (same as gpu)| yes        |
| non-GPU software | `force`           | false        | gpu              | yes        |
| non-GPU software | `force`           | true         | gpu              | yes        |
| non-GPU software | `force-nodevice`  | false        | gpu              | no         |
| non-GPU software | `force-nodevice`  | true         | gpu              | yes        |
| GPU software     | `detect`          | false        | gpu              | yes        |
| GPU software     | `detect`          | true         | gpu              | yes        |
| GPU software     | `detect-nodevice` | false        | gpu              | no         |
| GPU software     | `detect-nodevice` | true         | gpu              | yes        |
| GPU software     | `force`           | false        | gpu              | yes        |
| GPU software     | `force`           | true         | gpu              | yes        |
| GPU software     | `force-nodevice`  | false        | gpu              | no         |
| GPU software     | `force-nodevice`  | true         | gpu              | yes        |

### CPU/GPU architectures

| easyconfig       | `--gpu` option    | GPU required | Partition result | GPU device |
|------------------|-------------------|--------------|------------------|------------|
| non-GPU software | `detect`          | false        | cpu              | no         |
| non-GPU software | `detect`          | true         | cpu              | no         |
| non-GPU software | `detect-nodevice` | false        | cpu              | no         |
| non-GPU software | `detect-nodevice` | true         | cpu              | no         |
| non-GPU software | `force`           | false        | gpu              | yes        |
| non-GPU software | `force`           | true         | gpu              | yes        |
| non-GPU software | `force-nodevice`  | false        | gpu              | no         |
| non-GPU software | `force-nodevice`  | true         | gpu              | yes        |
| GPU software     | `detect`          | false        | gpu              | yes        |
| GPU software     | `detect`          | true         | gpu              | yes        |
| GPU software     | `detect-nodevice` | false        | gpu              | no         |
| GPU software     | `detect-nodevice` | true         | gpu              | yes        |
| GPU software     | `force`           | false        | gpu              | yes        |
| GPU software     | `force`           | true         | gpu              | yes        |
| GPU software     | `force-nodevice`  | false        | gpu              | no         |
| GPU software     | `force-nodevice`  | true         | gpu              | yes        |

## Open OnDemand module index

The Open OnDemand module browser lists the installed modules from a JSON
index of the Lmod module database, instead of running `module` commands.
For the architectures with the `ondemand_mod_index` option set to `1` in
`ARCHS` (currently `zen5-ib` on brussel and on sofia), the Lmod cache
job that runs after a successful build, and the cache jobs submitted
with `submit_build.py -m only`, additionally run
`run_lmod_cache.py --create-spider-cache`. That uses Lmod's standalone
`spider` tool with the JSON reporter to dump the module database as a
JSON file in the `cacheDir` of the architecture.

The Open OnDemand servers point their `module_file_dir` configuration
option at that `cacheDir` and read the index file from there. The file
is only consumed by Open OnDemand: it has no effect on the Lmod cache
that the `module` command uses, which is the compiled system cache
created by the regular `--create-cache` step of the same job.

## Source file fetching

Several build jobs may want to fetch the same source file, for example
when a whole set of easyconfigs is submitted at once. To prevent
duplicate downloads, the EasyBuild hooks that run inside every build job
use a lockfile per source file: a source file is only fetched by a job
while it holds its lock.

Each source file has its own lockfile in the `.locks` subdirectory of the
first EasyBuild source path, named after the flattened source file path.
The locks are implemented with [flufl.lock](https://pypi.org/project/flufl.lock/),
which is hardlink-based and therefore also works on shared filesystems.

A job that cannot acquire the lock of a source file waits for it,
rechecking every 60 seconds for up to 30 minutes. If the lock is still
held after that time, the build is aborted.

The owner of a lockfile is recorded in the lockfile itself. A lock is
considered stale when the owner is a process on the same host that no
longer exists, for example because the build was killed. Stale locks are
removed automatically, which allows the waiting job to acquire the lock.
Locks owned by processes on other hosts are never removed, because their
owner cannot be checked reliably.

When the build is killed, a lock is not always released by the post-fetch
hook. In that case, the lock expires after its lifetime of 3 hours and
can be acquired again.

In addition, when `submit_build.py` is run with the `-n` (`--pre-fetch`)
option, all missing source files of the easyconfigs and their dependencies
are fetched in a separate step before the build jobs are submitted, so
that the jobs usually find the sources already fetched. This step ignores
the fetch locks.

