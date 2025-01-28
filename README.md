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

```
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
python -m pip install flufl.lock pytest
# Install build_tools
cd /path/to/build_tools/
python -m pip install . --no-deps
```

## Testing

Tests can be carried out with `pytest`:

```
cd build_tools
python -m pytest
```
