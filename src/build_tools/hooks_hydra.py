#
# Copyright 2017-2024 Vrije Universiteit Brussel
# All rights reserved.
#
# This file is part of build_tools (https://github.com/vub-hpc/build_tools),
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
##
"""
Custom EasyBuild hooks for VUB-HPC Clusters

@author: Samuel Moors (Vrije Universiteit Brussel)
@author: Alex Domingo (Vrije Universiteit Brussel)
"""

import os
from pathlib import Path
import sys
import time

from flufl.lock import Lock, TimeOutError, NotLockedError

from easybuild.framework.easyconfig.constants import EASYCONFIG_CONSTANTS
from easybuild.framework.easyconfig.easyconfig import letter_dir_for, get_toolchain_hierarchy
from easybuild.tools import LooseVersion
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.config import BuildOptions, ConfigurationVariables, source_paths, update_build_option
from easybuild.tools.filetools import mkdir
from easybuild.tools.hooks import SANITYCHECK_STEP

from build_tools.clusters import ARCHS
from build_tools.ib_modules import IB_MODULE_SOFTWARE, IB_MODULE_SUFFIX, IB_OPT_MARK

# permission groups for licensed software
SOFTWARE_GROUPS = {
    'ABAQUS': 'babaqus',
    'ADF': 'badf',
    'AMS': 'badf',
    'CASTEP': 'bcastep',
    'COMSOL': 'bcomsol_users',  # autogroup (bcomsol, bcomsol_efremov)
    'FLUENT': 'bansys',
    'Gaussian': 'brusselall',  # site license
    'GaussView': 'brusselall',  # site license
    'Gurobi': 'brusselall',  # site license
    'Lumerical': 'bphot',
    'Mathematica': 'brusselall',  # site license
    'MATLAB': 'brusselall',  # site license
    'Morfeo': 'bmorfeo',
    'Q-Chem': 'bqchem',
    'QuantumATK': 'bquantumatk',
    'ReaxFF': 'breaxff',
    'Stata': 'brusselall',  # site license
    'VASP': 'bvasp',
}

GPU_ARCHS = [x for (x, y) in ARCHS.items() if y['partition']['gpu']]

LOCAL_ARCH = os.getenv('VSC_ARCH_LOCAL')
LOCAL_ARCH_SUFFIX = os.getenv('VSC_ARCH_SUFFIX')
LOCAL_ARCH_FULL = f'{LOCAL_ARCH}{LOCAL_ARCH_SUFFIX}'

VALID_TCGENS = ['2022a', '2023a']
VALID_MODULES_SUBDIRS = VALID_TCGENS + ['system']
VALID_TCS = ['foss', 'intel', 'gomkl', 'gimkl', 'gimpi']

SUBDIR_MODULES_BWRAP = '.modules_bwrap'


def get_tc_versions():
    " build dict of valid (sub)toolchain-version combinations per valid generation "
    tc_versions = {}
    for toolcgen in VALID_TCGENS:
        tc_versions[toolcgen] = []
        for toolc in VALID_TCS:
            try:
                tc_versions[toolcgen].extend(get_toolchain_hierarchy({'name': toolc, 'version': toolcgen}))
            except EasyBuildError:
                # skip if no easyconfig found for toolchain-version
                pass

    return tc_versions


def calc_tc_gen(name, version, tcname, tcversion, easyblock):
    """
    calculate the toolchain generation
    return False if not valid
    """
    name_version = {'name': name, 'version': version}
    toolchain = {'name': tcname, 'version': tcversion}
    software = [name, version, tcname, tcversion, easyblock]

    tc_versions = get_tc_versions()

    # (software with) valid (sub)toolchain-version combination
    for toolcgen in VALID_TCGENS:
        if toolchain in tc_versions[toolcgen] or name_version in tc_versions[toolcgen]:
            log_msg = f"Determined toolchain generation {toolcgen} for {software}"
            return toolcgen, log_msg

    # invalid toolchains
    # all toolchains have 'system' toolchain, so we need to handle the invalid toolchains separately
    # all toolchains have 'Toolchain' easyblock, so checking the easyblock is sufficient
    if easyblock == 'Toolchain':
        log_msg = f"Invalid toolchain {name} for {software}"
        return False, log_msg

    # software with 'system' toolchain: return 'system'
    if tcname == 'system':
        log_msg = f"Determined toolchain {tcname} for {software}"
        return tcname, log_msg

    log_msg = f"Invalid toolchain {tcname} and/or toolchain version {tcversion} for {software}"
    return False, log_msg


def update_module_install_paths(self):
    """
    update module install paths unless subdir-modules uption is specified "
    default subdir_modules config var = 'modules'
    here we set it to 'modules/<subdir>', where subdir can be any of VALID_MODULES_SUBDIRS
    exception: with bwrap it is set to SUBDIR_MODULES_BWRAP
    """
    configvars = ConfigurationVariables()
    subdir_modules = list(Path(configvars['subdir_modules']).parts)

    do_bwrap = subdir_modules == [SUBDIR_MODULES_BWRAP]

    log_format_msg = '[pre-fetch hook] Format of option subdir-modules %s is not valid. Must be modules/<subdir>'
    if len(subdir_modules) not in [1, 2]:
        raise EasyBuildError(log_format_msg, os.path.join(*subdir_modules))

    if not (subdir_modules[0] == 'modules' or subdir_modules != ['modules'] or do_bwrap):
        raise EasyBuildError(log_format_msg, os.path.join(*subdir_modules))

    if len(subdir_modules) == 2:
        subdir = subdir_modules[1]

        if subdir not in VALID_MODULES_SUBDIRS:
            log_msg = "[pre-fetch hook] Specified modules subdir %s is not valid. Choose one of %s"
            raise EasyBuildError(log_msg, subdir, VALID_MODULES_SUBDIRS)

        log_msg = "[pre-fetch hook] Option subdir-modules was set to %s, not updating module install paths"
        self.log.info(log_msg, subdir_modules)
        return

    subdir, log_msg = calc_tc_gen(
        self.name, self.version, self.toolchain.name, self.toolchain.version, self.cfg.easyblock)

    if not subdir:
        raise EasyBuildError("[pre-fetch hook] " + log_msg)

    self.log.info("[pre-fetch hook] " + log_msg)

    mod_filepath = Path(self.mod_filepath).parts

    if do_bwrap:
        self.log.info("[pre-fetch hook] Installing in new namespace with bwrap")
        real_mod_filepath = Path().joinpath(*mod_filepath[:-4], 'modules', subdir, *mod_filepath[-3:]).as_posix()

        # write the real module file path to stderr
        # after installation, the module file is copied to the real path
        sys.stderr.write(f'BUILD_TOOLS: real_mod_filepath {real_mod_filepath}\n')
        return

    # insert subdir into self.installdir_mod and self.mod_filepath
    installdir_mod = Path(self.installdir_mod).parts
    self.installdir_mod = Path().joinpath(*installdir_mod[:-1], subdir, installdir_mod[-1]).as_posix()
    self.log.info('[pre-fetch hook] Updated installdir_mod to %s', self.installdir_mod)

    real_mod_filepath = Path().joinpath(*mod_filepath[:-3], subdir, *mod_filepath[-3:]).as_posix()
    self.mod_filepath = real_mod_filepath
    self.log.info('[pre-fetch hook] Updated mod_filepath to %s', self.mod_filepath)


def acquire_fetch_lock(self):
    " acquire fetch lock "
    source_path = source_paths()[0]
    full_source_path = os.path.join(source_path, letter_dir_for(self.name), self.name)
    lock_name = full_source_path.replace('/', '_') + '.lock'

    lock_dir = os.path.join(source_path, '.locks')
    mkdir(lock_dir, parents=True)

    wait_time = 0
    wait_interval = 60
    wait_limit = 3600

    lock = Lock(os.path.join(lock_dir, lock_name), lifetime=wait_limit, default_timeout=1)
    self.fetch_hook_lock = lock

    while True:
        try:
            # try to acquire the lock
            lock.lock()
            self.log.info("[pre-fetch hook] Lock acquired: %s", lock.lockfile)
            break

        except TimeOutError as err:
            if wait_time >= wait_limit:
                error_msg = "[pre-fetch hook] Maximum wait time for lock %s to be released reached: %s sec >= %s sec"
                raise EasyBuildError(error_msg, lock.lockfile, wait_time, wait_limit) from err

            msg = "[pre-fetch hook] Lock %s held by another build, waiting %d seconds..."
            self.log.debug(msg, lock.lockfile, wait_interval)
            time.sleep(wait_interval)
            wait_time += wait_interval


def release_fetch_lock(self):
    " release fetch lock "
    lock = self.fetch_hook_lock
    try:
        lock.unlock()
        self.log.info("[post-fetch hook] Lock released: %s", lock.lockfile)

    except NotLockedError:
        self.log.warning("[post-fetch hook] Could not release lock %s: was already released", lock.lockfile)


def parse_hook(ec, *args, **kwargs):  # pylint: disable=unused-argument
    """Alter build options and easyconfig parameters"""

    # disable robot for bwrap
    # must be done in a hook in case robot is set in an easystack, which takes precedence over cmd line options
    subdir_modules = ConfigurationVariables()['subdir_modules']
    robot = BuildOptions()['robot']
    if subdir_modules == SUBDIR_MODULES_BWRAP and robot is not None:
        update_build_option('robot', None)
        ec.log.warning("[parse hook] Disabled robot for bwrap")

    # PMIx deps and sanity checks for munge
    if ec.name == 'PMIx':
        # Add osdependency on munge-devel
        extradep = 'munge-devel'
        ec.log.info("[parse hook] Adding OS dependency on: %s", extradep)
        ec['osdependencies'].append(extradep)
        # Add sanity check on munge component
        ec.log.info("[parse hook] Adding sanity check on munge component")
        # PMIx-v4 does not have the specific plugin for psec-munge,
        # but now it has a plugin for Slurm that links to munge
        if LooseVersion(ec.version) >= LooseVersion('4.2'):
            pmix_slurm_lib = 'lib/pmix/pmix_mca_prm_slurm.so'
        elif LooseVersion(ec.version) >= LooseVersion('4.0'):
            pmix_slurm_lib = 'lib/pmix/mca_prm_slurm.so'
        else:
            pmix_slurm_lib = 'lib/pmix/mca_psec_munge.so'

        ec['sanity_check_paths']['files'].append(pmix_slurm_lib)

    # InfiniBand support
    if ec.name in IB_MODULE_SOFTWARE:
        # remove any OS dependency on libverbs in non-IB nodes
        if LOCAL_ARCH_SUFFIX != IB_MODULE_SUFFIX:
            pkg_ibverbs = EASYCONFIG_CONSTANTS['OS_PKG_IBVERBS_DEV'][0]
            ec['osdependencies'] = [d for d in ec['osdependencies'] if d != pkg_ibverbs]
            ec.log.info("[parse hook] Removed IB from OS dependencies on non-IB system: %s", ec['osdependencies'])

    # OpenFabrics support
    if ec.name == 'OpenMPI':
        # remove libfabric from OpenMPI on all partitions
        ec['dependencies'] = [d for d in ec['dependencies'] if 'libfabric' not in d]
        ec.log.info("[parse hook] Removed libfabric from dependency list")

    if ec.name == 'Gurobi':
        # use centrally installed Gurobi license file, and don't copy to installdir
        ec['license_file'] = '/apps/brussel/licenses/gurobi/gurobi.lic'
        ec.log.info(f"[parse hook] Set parameter license_file: {ec['license_file']}")
        ec['copy_license_file'] = False
        ec.log.info(f"[parse hook] Set parameter copy_license_file: {ec['copy_license_file']}")

    if ec.name == 'MATLAB':
        ec['license_file'] = '/apps/brussel/licenses/matlab/network.lic'
        ec.log.info(f"[parse hook] Set parameter license_file: {ec['license_file']}")
        # replace copy of license file in install dir with link to original license
        ec['postinstallcmds'] = [f'ln -sfb {ec["license_file"]} %(installdir)s/licenses/']
        ec.log.info(f"[parse hook] Set parameter postinstallcmds: {ec['postinstallcmds']}")

    if ec.name in SOFTWARE_GROUPS:
        ec['group'] = SOFTWARE_GROUPS[ec.name]
        ec.log.info(f"[parse hook] Set parameter group: {ec['group']}")

    # set optarch for intel compilers on AMD nodes
    optarchs_intel = {
        'zen2': 'march=core-avx2',
        # common-avx512 gives test failure for scipy
        # see https://github.com/easybuilders/easybuild-easyconfigs/pull/18875
        'zen4': 'march=rocketlake',
    }
    if LOCAL_ARCH in optarchs_intel and ec.toolchain.name in ['intel-compilers', 'iimpi', 'iimkl', 'intel']:
        optarch = ec.toolchain.options.get('optarch')
        # only set if not set in the easyconfig or if set to default value (i.e. True)
        if not optarch or optarch is True:
            ec.toolchain.options['optarch'] = optarchs_intel[LOCAL_ARCH]
            ec.log.info(f"[parse hook] Set optarch in parameter toolchainopts: {ec.toolchain.options['optarch']}")

    # skip installation of CUDA software in non-GPU architectures, only create module file
    is_cuda_software = 'CUDA' in ec.name or 'CUDA' in ec['versionsuffix']
    if is_cuda_software and LOCAL_ARCH_FULL not in GPU_ARCHS:
        # module_only steps: [MODULE_STEP, PREPARE_STEP, READY_STEP, POSTITER_STEP, SANITYCHECK_STEP]
        ec['module_only'] = True
        ec.log.info(f"[parse hook] Set parameter module_only: {ec['module_only']}")
        ec['skipsteps'] = [SANITYCHECK_STEP]
        ec.log.info(f"[parse hook] Set parameter skipsteps: {ec['skipsteps']}")

    # set cuda compute capabilities
    elif is_cuda_software:
        ec['cuda_compute_capabilities'] = ARCHS[LOCAL_ARCH_FULL]['cuda_cc']
        ec.log.info(f"[parse hook] Set parameter cuda_compute_capabilities: {ec['cuda_compute_capabilities']}")


def pre_fetch_hook(self):
    """Hook at pre-fetch level"""
    update_module_install_paths(self)
    acquire_fetch_lock(self)


def post_fetch_hook(self):
    """Hook at post-fetch level"""
    release_fetch_lock(self)


def pre_configure_hook(self, *args, **kwargs):  # pylint: disable=unused-argument
    """Hook at pre-configure level to alter configopts"""

    # PMIx settings:
    # - build with munge support to work with Slurm
    # - disable per-user configuration files to save disk accesses during job start-up
    if self.name == 'PMIx':
        self.log.info("[pre-configure hook] Enable munge support")
        self.cfg.update('configopts', "--with-munge")
        if LooseVersion(self.version) >= LooseVersion('2'):
            self.log.info("[pre-configure hook] Disable per-user configuration")
            self.cfg.update('configopts', "--disable-per-user-config-files")

    # InfiniBand support:
    if self.name in IB_MODULE_SOFTWARE:
        ec_param = IB_MODULE_SOFTWARE[self.name][0]

        # convert any non-list parameters to a list
        if ec_param == 'configopts':
            ec_config = self.cfg['configopts'].split(' ')
        else:
            ec_config = self.cfg[ec_param]

        # clean any settings about IB
        ib_free_config = [opt for opt in ec_config if not any(mark in opt for mark in IB_OPT_MARK)]

        # update IB settings
        if LOCAL_ARCH_SUFFIX == IB_MODULE_SUFFIX:
            self.log.info("[pre-configure hook] Enabling verbs in %s", self.name)
            ib_opt = IB_MODULE_SOFTWARE[self.name][1]
        else:
            self.log.info("[pre-configure hook] Disabling verbs in %s", self.name)
            ib_opt = IB_MODULE_SOFTWARE[self.name][2]

        ib_config = ib_free_config + [ib_opt]

        # consolidate changes
        if ec_param == 'configopts':
            self.cfg['configopts'] = ' '.join(ib_config)
        else:
            self.cfg[ec_param] = ib_config

        self.log.info("[pre-configure hook] Updated '%s': %s", ec_param, self.cfg[ec_param])


def pre_module_hook(self, *args, **kwargs):  # pylint: disable=unused-argument
    """Hook at pre-module level to alter module files"""

    # Must be done this way, updating self.cfg['modextravars']
    # directly doesn't work due to templating.
    en_templ = self.cfg.enable_templating
    self.cfg.enable_templating = False

    ##########################
    # ------ MPI ----------- #
    ##########################

    if self.name == 'OpenMPI':
        # set MPI communication type in Slurm (default is none)
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/4706
        slurm_mpi_type = None
        if LooseVersion(self.version) >= '3.0.0':
            slurm_mpi_type = 'pmix'
        elif LooseVersion(self.version) >= '2.1.0':
            slurm_mpi_type = 'pmi2'

        if slurm_mpi_type:
            self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
            self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

    if self.name == 'impi':
        # - use PMI1/2 implementation from Slurm
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7192
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7588

        # use PMI1 by default (works with older versions)
        slurm_mpi_type = None
        intel_mpi = {
            'pmi_var': 'I_MPI_PMI2',
            'pmi_set': 'no',
            'pmi_lib': '/usr/lib64/slurmpmi/libpmi.so',
        }

        if LooseVersion(self.version) >= '2019.7':
            # Intel MPI v2019 supports PMI2 with I_MPI_PMI=pmi2, but it only atually works since v2019.7
            # see https://bugs.schedmd.com/show_bug.cgi?id=6727
            intel_mpi['pmi_var'] = 'I_MPI_PMI'
            intel_mpi['pmi_set'] = 'pmi2'
            intel_mpi['pmi_lib'] = '/usr/lib64/slurmpmi/libpmi2.so'
            slurm_mpi_type = 'pmi2'
        elif LooseVersion(self.version) >= '2019.0':
            # use PMI1 with this buggy releases of Intel MPI
            # see https://bugs.schedmd.com/show_bug.cgi?id=6727
            intel_mpi['pmi_var'] = 'I_MPI_PMI'
            intel_mpi['pmi_set'] = 'pmi1'
        elif LooseVersion(self.version) >= '2018.0':
            # Intel MPI v2018 supports PMI2 with I_MPI_PMI2=yes
            intel_mpi['pmi_set'] = 'yes'
            intel_mpi['pmi_lib'] = '/usr/lib64/slurmpmi/libpmi2.so'
            slurm_mpi_type = 'pmi2'

        self.log.info("[pre-module hook] Set MPI bootstrap for Slurm")
        self.cfg['modluafooter'] = """
if ( os.getenv("SLURM_JOB_ID") ) then
    setenv("I_MPI_HYDRA_BOOTSTRAP", "slurm")
    setenv("I_MPI_PIN_RESPECT_CPUSET", "0")
    setenv("I_MPI_PMI_LIBRARY", "%(pmi_lib)s")
    setenv("%(pmi_var)s", "%(pmi_set)s")
end
""" % intel_mpi

        # set MPI communication type in Slurm (default is none, which works for PMI1)
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7192
        # more info: https://dev.azure.com/VUB-ICT/Directie%20ICT/_workitems/edit/7588
        if slurm_mpi_type:
            self.log.info("[pre-module hook] Set Slurm MPI type to: %s", slurm_mpi_type)
            self.cfg['modextravars'].update({'SLURM_MPI_TYPE': slurm_mpi_type})

    ##########################
    # ------ TUNING -------- #
    ##########################

    # set the maximum heap memory for Java applications to 80% of memory allocated to the job
    # more info: https://projects.cc.vub.ac.be/issues/2940
    if self.name == 'Java':
        self.log.info("[pre-module hook] Set max heap memory in Java module")
        self.cfg['modluafooter'] = """
local mem = get_avail_memory()
if mem then
    setenv("JAVA_TOOL_OPTIONS",  "-Xmx" .. math.floor(mem*0.8))
end
"""

    # set MATLAB Runtime Component Cache folder to a local temp dir
    # this cache directory lies in $HOME by default, which cause binaries compiled with MCC to hang
    if self.name == 'MATLAB':
        self.log.info("[pre-module hook] Set MATLAB Runtime Component Cache folder")
        self.cfg['modluafooter'] = """
setenv("MCR_CACHE_ROOT", os.getenv("TMPDIR") or pathJoin("/tmp", os.getenv("USER")))
"""

    ##########################
    # ------ LICENSES ------ #
    ##########################

    # set COMSOL licenses
    if self.name == 'COMSOL':
        self.cfg['modluafooter'] = """
if userInGroup("bcomsol") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License.dat")
elseif userInGroup("bcomsol_efremov") then
    setenv("LMCOMSOL_LICENSE_FILE", "/apps/brussel/licenses/comsol/License_efremov.dat")
end
"""

    # Morfeo license file
    if self.name == 'Morfeo':
        self.cfg['modextravars'].update({'CENAERO_LICENSE_FILE': '/apps/brussel/licenses/morfeo/license.lic'})

    # ABAQUS license file
    if self.name == 'ABAQUS':
        self.cfg['modextravars'].update({'ABAQUSLM_LICENSE_FILE': '/apps/brussel/licenses/abaqus/license.lic'})

    ##########################
    # ------ DATABASES ----- #
    ##########################

    apps_with_dbs = ["AlphaFold", "BUSCO", "ColabFold", "OpenFold"]

    if self.name in apps_with_dbs:
        self.cfg['modloadmsg'] = "%(name)s databases are located in /databases/bio/%(namelower)s-%(version)s"

    if self.name == 'BUSCO':
        if LooseVersion(self.version) >= '5.0.0':
            self.cfg['modloadmsg'] += """
Use local DBs with command: `busco --offline --download_path /databases/bio/BUSCO-5 ...`
"""

    if self.name == 'AlphaFold':
        self.cfg['modextravars'] = {
            'ALPHAFOLD_DATA_DIR': '/databases/bio/%(namelower)s-%(version)s',
        }

    # add links to our documentation for software covered in
    # https://hpc.vub.be/docs/software/usecases/
    doc_url = 'https://hpc.vub.be/docs/software/usecases/'
    doc_app = ['MATLAB', 'R', 'Gaussian', 'GaussView', 'matplotlib', ('CESM-deps', 'cesm-cime'), 'GAP', 'Mathematica',
               'Stata', 'GROMACS', 'CP2K', 'PyTorch', 'ORCA', 'SRA-Toolkit', 'AlphaFold', 'OpenFold', 'GAMESS-US']

    # generate links for documented apps
    app_anchors = [(app, app.lower()) if isinstance(app, str) else app for app in doc_app]
    app_links = {app: '#'.join([doc_url, anchor]) for (app, anchor) in app_anchors}

    if self.name in app_links:
        # update usage section
        usage_info = {'app': self.name, 'link': app_links[self.name]}
        usage_msg = """
Specific usage instructions for %(app)s are available in VUB-HPC documentation:
%(link)s
""" % usage_info
        self.cfg['usage'] = usage_msg + self.cfg['usage'] if self.cfg['usage'] else usage_msg
        # update documentation links
        if self.cfg['docurls']:
            self.cfg['docurls'].append(usage_info['link'])
        else:
            self.cfg['docurls'] = [usage_info['link']]

    #################################
    # ------ DUMMY MODULES -------- #
    #################################

    is_cuda_software = 'CUDA' in self.name or 'CUDA' in self.cfg['versionsuffix']
    if is_cuda_software and LOCAL_ARCH_FULL not in GPU_ARCHS:
        self.log.info("[pre-module hook] Creating dummy module for CUDA modules on non-GPU nodes")
        self.cfg['modluafooter'] = """
if mode() == "load" and not os.getenv("BUILD_TOOLS_LOAD_DUMMY_MODULES") then
    LmodError([[
This module is only available on nodes with a GPU.
Jobs can request GPUs with the command 'srun --gpus-per-node=1' or 'sbatch --gpus-per-node=1'.

More information in the VUB-HPC docs:
https://hpc.vub.be/docs/job-submission/gpu-job-types/#gpu-jobs
    ]])
end"""

    ############################
    # ------ FINALIZE -------- #
    ############################

    self.cfg.enable_templating = en_templ


def post_build_and_install_loop_hook(ecs_with_res):
    """
    Hook to run after all easyconfigs have been built and installed

    :param ecs_with_res: list of easyconfig tuples, where each tuple consists of 2 dicts:
                         the easyconfig data and the build status data.
    """

    installed_modules = [x[0]['full_mod_name'] for x in ecs_with_res if x[1]['success']]
    if installed_modules:
        sys.stderr.write(f'BUILD_TOOLS: builds_succeeded {" ".join(installed_modules)}\n')
