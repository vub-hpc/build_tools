# build_tools

Tools to build and install software

## Testing

cd build_tools/src
python3 -m pytest ../tests --fromsource

## Installation

Install the EasyBuild dependencies in editable mode and make sure that you use the main branch of each repo. `pip` only knows about stable releases. Therefore, if you install a development version, it will **not** fulfill the version requirements in `pip`. This is not a big issue, because by installing in editable mode, we can make any changes to the code later on.

```
cd easybuild-easyconfigs/
git checkout main
pip install --user --editable .
git checkout develop
```

Repeat for all EasyBuild repos and then install `build_tools` as usual

```
cd build_tools
python3 -m pip install --user .
```
