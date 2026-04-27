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
installations and that breaks EasyBuild. In such cases, make sure to enable `compat` mode for the editable installation:

```
pip install -e . --config-settings editable_mode=compat
```
See https://github.com/easybuilders/easybuild-framework/issues/4451

Newer versions of `setuptools` can cause trouble to install `vsc-base` and `vsc-utils` with `pip`. In such case, install the VSC packages with the traditional

```
python setup.py install
```

### Virtual environment

```bash
python -m venv /path/to/venv/hpcbuild
source /path/to/venv/hpcbuild/activate
# Install VSC dependencies
cd /path/to/vsc-install/
python3 setup.py install
cd /path/to/vsc-base/
python3 setup.py install
cd /path/to/vsc-utils/
python3 setup.py install
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
python -m pip install vsc-install --no-build-isolation
python -m pip install vsc-base vsc-utils --no-build-isolation
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

## Testing

Tests can be carried out with `pytest`:

```bash
cd build_tools
python -m pytest
```
